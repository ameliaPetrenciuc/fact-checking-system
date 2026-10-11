from typing import Optional, Dict, Any
from pydantic import BaseModel
from crewai.flow.flow import Flow, start, listen

from agents.crew_agents import kg_analyst_agent, web_explainer_agent
from agents.fact_check_crew import run_adversarial_deliberation
from config.database import get_session
from graph.vector_index import find_best_semantic_match
from graph.repository import save_web_result_to_graph
from pipeline.explanation import build_memory_response
from pipeline.orchestrator import (
    resolve_web_persistence_plan,
    run_ontology_extraction,
    run_web_investigation,
    gather_web_evidence,
)


class FactCheckState(BaseModel):
    user_text: str = ""

    kg_raw_result: Optional[Dict] = None
    kg_memory_response: Optional[Dict] = None
    needs_web: bool = True

    web_result: Optional[Dict] = None
    verified_triples: Optional[list] = None

    final_answer: str = ""
    final_explanation: str = ""


class FactCheckFlow(Flow[FactCheckState]):

    @start()
    def check_knowledge_graph(self):
        query_text = self.state.user_text

        with get_session() as session:
            cached_result = session.execute_read(
                find_best_semantic_match,
                query_text
            )

        if cached_result:
            memory_response = build_memory_response(cached_result)

            self.state.kg_raw_result = cached_result
            self.state.kg_memory_response = memory_response
            self.state.needs_web = memory_response["needs_web"]
            self.state.final_answer = memory_response["final_answer"]
            self.state.final_explanation = memory_response["explanation"]

            print("[FLOW]  Semantic match found in KG.")
        else:
            self.state.needs_web = True
            print("[FLOW]  No sufficient KG result. Needs web investigation.")

        return self.state.needs_web

    @listen(check_knowledge_graph)
    def explain_kg_result(self, needs_web):

        if needs_web or not self.state.kg_raw_result or not self.state.kg_memory_response:
            return needs_web

        print("[FLOW]  KG Analyst explaining result...")

        raw_result = self.state.kg_raw_result
        memory_response = self.state.kg_memory_response

        prompt = f"""
    You are explaining a fact-check result to a regular, non-technical user.

    IMPORTANT RULES:
    - Do NOT change the verdict.
    - Do NOT change the routing decision.
    - Do NOT invent any new fact.
    - Explain only what is already present in the data.
    - Write a clear explanation in 2-3 sentences.
    - Return ONLY the explanation text. No JSON. No markdown. No bullet points.
    - If Effective truth is FALSE and NLI relation is ENTAILMENT, explain that the user claim matches or paraphrases a claim already marked as false in the Knowledge Graph.
    - If Effective truth is FALSE, do NOT say the claim is "supported by the knowledge base" or "supported by reliable evidence".
    - If Effective truth is TRUE, you may say the claim is supported by verified knowledge in the graph.
    - If NLI relation is CONTRADICTION, explain that the user claim contradicts the matched claim/fact.
    
    RAW KG DATA:
    - Final answer: {self.state.final_answer}
    - Internal explanation: {memory_response.get("explanation")}
    - Matched claim/fact: {raw_result.get("matched_text")}
    - Similarity score: {raw_result.get("similarity_score")}
    - Strategy used: {raw_result.get("strategy_used")}
    - Memory verdict: {raw_result.get("verdict")}
    - Effective truth: {raw_result.get("effective_truth")}
    - NLI relation: {raw_result.get("nli_label")}
    - NLI score: {raw_result.get("nli_score")}
    - Source type: {raw_result.get("source_type")}

    Write the explanation now.
"""

        try:
            result = kg_analyst_agent.kickoff(prompt)
            explanation_text = str(result).strip()

            if explanation_text:
                self.state.final_explanation = explanation_text
                print("[FLOW]  KG explanation generated.")
        except Exception as e:
            print(f"[FLOW]  KG Analyst failed, keeping deterministic explanation: {e}")

        return needs_web

    @listen(explain_kg_result)
    def web_investigation_step(self, needs_web):
        if not needs_web:
            print("[FLOW]  Short-circuit from KG. Skipping web.")
            return False

        query_text = self.state.user_text

        print(f"[FLOW]  Gathering web evidence for: '{query_text}'")
        evidence_bundle = gather_web_evidence(query_text)

        if not evidence_bundle:
            self.state.final_answer = "NEUTRAL"
            self.state.final_explanation = "No relevant evidence found from trusted web sources."
            self.state.web_result = None
            return False

        evidence_passages = evidence_bundle.get("evidence_passages", [])

        if not evidence_passages:
            self.state.final_answer = "NEUTRAL"
            self.state.final_explanation = "No relevant evidence passages were found from trusted sources."
            self.state.web_result = None
            return False

        scores = []
        for passage in evidence_passages:
            try:
                scores.append(float(passage.get("score", 0)))
            except (TypeError, ValueError):
                scores.append(0.0)

        max_score = max(scores, default=0.0)

        if max_score < 0.40:
            self.state.final_answer = "NEUTRAL"
            self.state.final_explanation = (
                "Evidence was found, but its relevance score was too low for a confident verdict."
            )
            self.state.web_result = None
            return False

        print("[FLOW]  Launching Adversarial Deliberation Tribunal...")
        web_result = run_adversarial_deliberation(query_text, evidence_bundle)

        if not web_result:
            print("[FLOW]  Tribunal failed. Falling back to direct pipeline...")
            web_result = run_web_investigation(query_text)

        if not web_result:
            self.state.final_answer = "NEUTRAL"
            self.state.final_explanation = "Web investigation failed or returned no results."
            self.state.web_result = None
            return False

        _VERDICT_MAP = {
            "TRUE": "TRUE", "FALSE": "FALSE", "NEUTRAL": "NEUTRAL",
            "PARTIALLY_SUPPORTED": "TRUE", "PARTIALLY SUPPORTED": "TRUE",
            "SUPPORTED": "TRUE", "UNSUPPORTED": "NEUTRAL",
        }
        verdict = str(web_result.get("verdict", "NEUTRAL")).upper().strip().replace(".", "")
        verdict = _VERDICT_MAP.get(verdict, "NEUTRAL")

        web_result["verdict"] = verdict

        self.state.web_result = web_result
        self.state.final_answer = verdict
        self.state.final_explanation = web_result.get("explanation", "N/A")

        print(f"[FLOW] Web verdict: {self.state.final_answer}")
        return self.state.final_answer != "NEUTRAL"

    @listen(web_investigation_step)
    def explain_web_result(self, should_continue):

        if not should_continue or not self.state.web_result:
            return should_continue

        print("[FLOW]  Web Explainer explaining result...")

        web_result = self.state.web_result
        evidence_passages = web_result.get("evidence_passages", [])

        formatted_passages = []
        for i, passage in enumerate(evidence_passages, start=1):
            formatted_passages.append(
                f"Passage {i}:\n"
                f"- Source URL: {passage.get('source_url')}\n"
                f"- Relevance score: {passage.get('score')}\n"
                f"- Extracted text: {passage.get('content')}\n"
            )

        joined_passages = "\n".join(formatted_passages) if formatted_passages else "No evidence passages available."

        deliberation_section = ""
        if web_result.get("deliberation_used"):
            deliberation_section = (
                f"\n        ADVERSARIAL DELIBERATION CONTEXT:\n"
                f"        This verdict was reached through a structured multi-agent tribunal.\n"
                f"        - Supporting evidence summary: {web_result.get('support_summary', 'N/A')}\n"
                f"        - Contradicting evidence summary: {web_result.get('contradiction_summary', 'N/A')}\n"
                f"        Mention briefly that this verdict was reached after weighing evidence from both sides.\n"
            )

        prompt = f"""
        You are explaining a web-based fact-check result to a regular, non-technical user.

        IMPORTANT RULES:
        - Do NOT change the verdict.
        - Do NOT invent any evidence.
        - Use only the passages and URLs provided below.
        - Clearly mention which source(s) support the explanation.
        - Quote or paraphrase the extracted evidence faithfully.
        - Mention the corrected claim if it exists and helps clarify the truth.
        - Keep the explanation concise, clear, and honest.
        - Write 2-4 sentences maximum.
        - Return ONLY the explanation text. No JSON. No markdown. No bullet points.

        WEB FACT-CHECK RESULT:
        - Verdict: {web_result.get("verdict")}
        - Existing explanation: {web_result.get("explanation")}
        - Corrected claim: {web_result.get("corrected_claim")}
        - Primary source URL: {web_result.get("primary_url")}
        - Confidence: {web_result.get("confidence")}
        {deliberation_section}
        TOP EVIDENCE PASSAGES:
        {joined_passages}

        Write the explanation now.
        """

        try:
            result = web_explainer_agent.kickoff(prompt)
            explanation_text = str(result).strip()

            if explanation_text:
                self.state.final_explanation = explanation_text
                print("[FLOW]  Web explanation generated.")
        except Exception as e:
            print(f"[FLOW]  Web Explainer failed, keeping original web explanation: {e}")

        return should_continue

    @listen(explain_web_result)
    def ontology_extraction_step(self, should_continue):
        if not should_continue:
            return {
                "answer": self.state.final_answer,
                "explanation": self.state.final_explanation,
                "triples_saved": 0
            }

        print("[FLOW] 🧬 Executing native ontology extraction (Direct Python Call)...")

        web_result = self.state.web_result or {}
        print(f"\n[DEBUG] Evidence Text length: {len(web_result.get('evidence_text', ''))}")
        print(f"[DEBUG] Evidence Passages length: {len(web_result.get('evidence_passages', []))}")
        claim_text = self.state.user_text

        try:
            verified_triples = run_ontology_extraction(claim_text, web_result)
        except Exception as e:
            print(f"[FLOW]  Ontology extraction failed: {e}")
            verified_triples = []

        self.state.verified_triples = verified_triples

        print(f"[FLOW]  Ontology extraction produced {len(verified_triples)} verified triples.")
        return len(verified_triples)

    @listen(ontology_extraction_step)
    def update_knowledge_graph(self, triples_count):

        if not self.state.web_result or self.state.final_answer == "NEUTRAL":
            return {
                "answer": self.state.final_answer,
                "explanation": self.state.final_explanation,
                "triples_saved": 0
            }

        verdict = str(self.state.web_result.get("verdict", "NEUTRAL")).upper().strip().replace(".", "")
        if verdict not in ("TRUE", "FALSE", "NEUTRAL"):
            verdict = "NEUTRAL"

        if verdict == "NEUTRAL":
            return {
                "answer": verdict,
                "explanation": self.state.final_explanation,
                "triples_saved": 0
            }

        original_explanation = self.state.web_result.get("explanation", "N/A")
        primary_url = self.state.web_result.get("primary_url")
        verified_triples = self.state.verified_triples or []

        claim_text = self.state.user_text

        persistence_plan = resolve_web_persistence_plan(
            claim_text,
            self.state.web_result
        )

        print(f"[FLOW]  Persistence plan: {persistence_plan}")

        if persistence_plan["mode"] != "store_nothing":
            try:
                with get_session() as session:
                    session.execute_write(
                        save_web_result_to_graph,
                        persistence_plan["false_claim_text"],
                        persistence_plan["true_claim_text"],
                        original_explanation,
                        primary_url,
                        verified_triples
                    )
                print("[FLOW]  Knowledge archived in Neo4j.")
            except Exception as e:
                print(f"[FLOW]  Error while saving to graph: {e}")
        else:
            print("[FLOW]  No persistence needed for this result.")

        return {
            "answer": verdict,
            "explanation": self.state.final_explanation,
            "triples_saved": len(verified_triples)
        }