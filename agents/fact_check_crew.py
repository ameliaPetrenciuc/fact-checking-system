import json
import re
from typing import Optional, List, Dict

from crewai import Crew, Task, Process

from agents.crew_agents import (
    claim_advocate_agent,
    claim_challenger_agent,
    verdict_judge_agent,
)


def run_adversarial_deliberation(claim: str, evidence_bundle: Dict) -> Optional[Dict]:

    evidence_passages = evidence_bundle.get("evidence_passages", [])
    evidence_text = evidence_bundle.get("evidence_text", "")
    sources = evidence_bundle.get("sources", [])

    formatted_evidence = _format_evidence_for_agents(evidence_passages)

    advocate_task = Task(
        description=(
            f'You are the EVIDENCE SUPPORT ANALYST in a fact-checking tribunal.\n\n'
            f'CLAIM UNDER REVIEW: "{claim}"\n\n'
            f'EVIDENCE GATHERED FROM TRUSTED SOURCES:\n{formatted_evidence}\n\n'
            f'YOUR SCOPE — SUPPORT ONLY:\n'
            f'List ONLY passages that SUPPORT or PARTIALLY SUPPORT the claim.\n\n'
            f'For each supporting passage, specify:\n'
            f'- Which evidence passage by number and its source URL\n'
            f'- Whether the support is DIRECT, PARTIAL, or WEAK\n'
            f'- Any conditions or limitations mentioned in the evidence\n\n'
            f'STRICT PROHIBITIONS:\n'
            f'- You are FORBIDDEN from quoting, paraphrasing, analyzing, or referencing '
            f'any passage that contradicts, refutes, or weakens the claim. That is the '
            f'Contradiction Analyst\'s exclusive role.\n'
            f'- You are FORBIDDEN from concluding that "the claim is not supported", '
            f'"contradicts the claim", or "the evidence indicates the opposite". '
            f'Do NOT explain WHY there is no support.\n'
            f'- If NO passage supports the claim, your ENTIRE output must be exactly:\n'
            f'  "No supporting evidence was found in the provided passages."\n'
            f'  Do not add anything else. Do not describe the contradicting passages. Stop.\n\n'
            f'IF SUPPORT EXISTS:\n'
            f'- MAGNITUDE / QUALIFIER CHECK: If the claim contains a qualifier such as '
            f'"moderate", "strong", "weak", "low", "high", "significant", "limited", '
            f'"mild", "severe", "substantial", or "robust", do NOT mark the claim as DIRECTLY supported '
            f'unless the evidence explicitly supports that qualifier or provides an equivalent quantitative/contextual measure.\n'
            f'- Evidence that only supports the general phenomenon, but not the qualifier, must be described as WEAK or PARTIAL support and explicitly marked as NOT sufficient for a TRUE verdict.\n'
            f'- Do NOT invent connections that are not explicitly in the evidence.\n'
            f'- Do NOT use outside knowledge.\n'
            f'- Structure your analysis in 3-5 clear sentences with citations.\n\n'
            f'Write your analysis now.'
        ),
        expected_output=(
            "Either a 3-5 sentence enumeration of supporting evidence with DIRECT/PARTIAL/WEAK "
            "labels and source URL citations, OR the exact single sentence "
            "\"No supporting evidence was found in the provided passages.\" if no support exists. "
            "Never any discussion of contradicting passages."
        ),
        agent=claim_advocate_agent,
    )

    challenger_task = Task(
        description=(
            f'You are the EVIDENCE CONTRADICTION ANALYST in a fact-checking tribunal.\n\n'
            f'CLAIM UNDER REVIEW: "{claim}"\n\n'
            f'EVIDENCE GATHERED FROM TRUSTED SOURCES:\n{formatted_evidence}\n\n'
            f'Analyze the evidence above and identify any passages that CONTRADICT, '
            f'WEAKEN, NARROW, or CONTEXTUALIZE the claim.\n\n'
            f'For each counter-point, specify:\n'
            f'- Which evidence passage by number and its source URL\n'
            f'- The issue type: CONTRADICTION, NARROWING, MISSING CONTEXT, OVERGENERALIZATION, or UNSUPPORTED QUALIFIER\n'
            f'- What the evidence actually says versus what the claim states\n\n'
            f'IMPORTANT RULES:\n'
            f'- Your job is NOT to summarize supporting evidence.\n'
            f'- Do NOT repeat the Support Analyst role.\n'
            f'- If the evidence supports the claim and no contradiction is found, say that clearly in the first sentence.\n'
            f'- Then mention only real limitations, narrowing, missing context, or conditions if they exist.\n'
            f'- If there are no meaningful limitations, say "No contradiction or meaningful limitation was found."\n'
            f'- Do NOT invent contradictions that are not explicitly in the evidence.\n'
            f'- Do NOT use outside knowledge — only the passages above.\n'
            f'- If the evidence supports only the broad topic but fails to support an important qualifier '
            f'in the claim, such as "moderate", "strong", "weak", "low", "high", "significant", '
            f'"limited", "mild", "severe", "substantial", or "robust", identify this as UNSUPPORTED QUALIFIER or OVERGENERALIZATION.\n'
            f'- Structure your analysis in 3-5 clear sentences with citations.\n\n'
            ),
        expected_output=(
            "A 3-5 sentence objective assessment identifying any contradictions, narrowing, "
            "or missing context, with source URL citations. Must explicitly conclude "
            "'No meaningful contradiction was found' if the evidence aligns with the claim."
        ),
        agent=claim_challenger_agent,
    )

    judge_task = Task(
        description=(
            f'You are the CHIEF JUDGE presiding over this fact-checking tribunal.\n\n'
            f'CLAIM: "{claim}"\n\n'
            f'RAW EVIDENCE FROM TRUSTED SOURCES:\n{formatted_evidence}\n\n'
            f'You have reviewed:\n'
            f'1. The raw evidence gathered from trusted web sources.\n'
            f'2. The Support Analyst findings.\n'
            f'3. The Contradiction Analyst findings.\n\n'
            f'Deliver your FINAL VERDICT by weighing the quality and specificity of cited evidence.\n\n'
            f'VERDICT RULES:\n'
            f'- TRUE: Supporting evidence is strong, directly relevant, and authoritative. '
            f'Minor contradictions from earlier or smaller studies do NOT prevent TRUE if a '
            f'larger or more authoritative source confirms the claim.\n'
            f'- FALSE: The STRONGEST available evidence (largest trial, most authoritative source) '
            f'clearly and DIRECTLY refutes the claim, OR a credible fact-checker explicitly debunks it.\n'
            f'- NEUTRAL: Use when evidence is absent, off-topic, only indirectly related, or insufficient '
            f'to verify the exact claim. NEUTRAL is not a failure; it is the correct verdict when the '
            f'evidence does not directly support or refute the claim. However, do not choose NEUTRAL '
            f'if the available evidence clearly supports or refutes the core assertion.\n'
            f'DECISION PRINCIPLES:\n'
            f'- Arguments or findings WITHOUT a cited source URL carry ZERO weight.\n'
            f'- Ignore rhetorical quality. Focus only on evidence specificity and relevance.\n'
            f'- A single strong, directly relevant source can outweigh multiple weak passages.\n'
            f'- EVIDENCE CONTENT OVER SBERT SCORES: Relevance scores are a rough signal only. '
            f'Read the actual text of each passage and reason about its logical relationship to the claim. '
            f'A passage with score 0.42 that directly addresses the claim topic is VALID evidence. '
            f'Only discard passages whose text is clearly unrelated to the claim subject.\n'
            f'- TOPICAL MATCH IS NOT ENOUGH: A passage can mention the same entities or topic as the claim '
            f'but still fail to verify it. If the passage discusses the TOPIC but does NOT explicitly confirm '
            f'the SPECIFIC ASSERTION made by the claim, use NEUTRAL. '
            f'Example: A passage about "blood proteins in COVID patients" does NOT verify a claim about '
            f'"lack of consensus" among those proteins. A passage about "SARS-CoV-2 homology" does NOT '
            f'verify a claim about "different species" without explicit species classification.\n'
            f'- MAGNITUDE / QUALIFIER RULE: If the claim contains a qualifier such as '
            f'"moderate", "strong", "weak", "low", "high", "significant", "limited", '
            f'"mild", "severe", "substantial", "robust", or "modest", the evidence must explicitly support '
            f'that qualifier or provide an equivalent quantitative/contextual measure. Evidence that only confirms '
            f'the general phenomenon is NOT enough for TRUE. For example, evidence that a vaccine induces an immune response '
            f'does NOT verify the claim that it induces a moderate immune response unless "moderate" or an equivalent magnitude is supported. '
            f'If the qualifier is not verified, choose NEUTRAL unless the evidence directly refutes it.\n'
            f'- RELATEDNESS IS NOT CONFIRMATION: If evidence says two entities are "related", "homologous", '
            f'or "similar", this does NOT confirm they are "different" or "the same". Relatedness is a '
            f'spectrum. Only use TRUE if the evidence EXPLICITLY states the exact relationship claimed.\n'
            f'- NUANCE MATTERS: Many scientific claims use hedging language ("may help", "is associated with", '
            f'"suggests"). If the claim uses cautious language AND the evidence confirms the same finding with '
            f'the same key conditions, verdict is TRUE. Caveats do not make a hedged claim false. However, if the '
            f'evidence only supports a narrower, condition-specific, or partial version of the claim, choose NEUTRAL.\n'
            f'- CONFIRMATION SIGNAL: If evidence from authoritative sources (medical journals, WHO, CDC, '
            f'university research) directly confirms the claim\'s core assertion, verdict is TRUE — even if '
            f'some passages add context, limitations, or later updates. Context is not contradiction.\n'
            f'- MIXED EVIDENCE → TRUE (not FALSE): When multiple studies report contradictory results '
            f'about a treatment or finding, and AT LEAST ONE large-scale or authoritative study confirms '
            f'the claim, verdict is TRUE. Early negative studies do NOT override later confirmatory '
            f'evidence. Weight the strongest/largest source, not the most contradictory one.\n'
            f'- PARTIAL DEBUNK → FALSE: If the evidence DIRECTLY and EXPLICITLY refutes the core assertion '
            f'of the claim (not just adds nuance or context), verdict is FALSE. Missing evidence for a '
            f'secondary subpoint does NOT mandate FALSE or NEUTRAL.\n'
            f'- DEBUNKING SIGNAL: If an evidence passage comes from a fact-check article '
            f'(e.g. boomlive.in, snopes.com, factcheck.org, fullfact.org, leadstories.com) AND explicitly '
            f'states the SPECIFIC claim is "debunked", "refuted", or "found false", '
            f'treat that as strong contradiction evidence. However, verify that the debunked claim matches '
            f'YOUR claim — fact-checkers often debunk a DIFFERENT version of a similar claim.\n\n'
            f'CORRECTED CLAIM:\n'
            f'- Required if verdict is FALSE.\n'
            f'- Must be a single, direct, atomic declarative assertion.\n'
            f'- FORBIDDEN: "There is no evidence that...", "Studies show...", "According to..."\n'
            f'- GOOD example: "Garlic does not cure COVID-19."\n\n'
            f'Respond with ONLY a valid JSON object:\n'
            f'{{\n'
            f'  "verdict": "TRUE" or "FALSE" or "NEUTRAL",\n'
            f'  "explanation": "2-3 sentence explanation citing key evidence",\n'
            f'  "confidence": 0.0 to 1.0,\n'
            f'  "corrected_claim": "corrected assertion if FALSE, null otherwise",\n'
            f'  "primary_url": "URL of the most authoritative source cited",\n'
            f'  "support_summary": "one sentence: strongest supporting evidence found",\n'
            f'  "contradiction_summary": "one sentence: strongest contradicting evidence found"\n'
            f'}}'
        ),
        expected_output=(
            "A valid JSON object with keys: verdict, explanation, confidence, "
            "corrected_claim, primary_url, support_summary, contradiction_summary."
        ),
        agent=verdict_judge_agent,
        context=[advocate_task, challenger_task],
    )

    deliberation_crew = Crew(
        agents=[
            claim_advocate_agent,
            claim_challenger_agent,
            verdict_judge_agent,
        ],
        tasks=[advocate_task, challenger_task, judge_task],
        verbose=True,
        process=Process.sequential,
    )

    print(f"\n{'' * 20}")
    print("  ADVERSARIAL FACT-CHECK TRIBUNAL CONVENED")
    print(f"  Claim: \"{claim[:80]}{'...' if len(claim) > 80 else ''}\"")
    print(f"  Evidence: {len(evidence_passages)} passages from {len(sources)} sources")
    print("  Phases: Support Analyst → Contradiction Analyst → Judge")
    print(f"{'⚖️ ' * 20}\n")

    try:
        crew_output = deliberation_crew.kickoff()

        tasks_out = crew_output.tasks_output
        support_raw = tasks_out[0].raw if len(tasks_out) > 0 else ""
        contradiction_raw = tasks_out[1].raw if len(tasks_out) > 1 else ""
        judge_raw = tasks_out[2].raw if len(tasks_out) > 2 else crew_output.raw

        verdict_data = _parse_judge_verdict(judge_raw)

        _VERDICT_MAP = {
            "TRUE": "TRUE",
            "FALSE": "FALSE",
            "NEUTRAL": "NEUTRAL",
            "PARTIALLY_SUPPORTED": "TRUE",
            "PARTIALLY SUPPORTED": "TRUE",
            "SUPPORTED": "TRUE",
            "UNSUPPORTED": "NEUTRAL",
        }
        verdict = str(verdict_data.get("verdict", "NEUTRAL")).upper().strip().replace(".", "")
        verdict = _VERDICT_MAP.get(verdict, "NEUTRAL")

        result = {
            "verdict": verdict,
            "explanation": verdict_data.get("explanation", "Deliberation completed."),
            "confidence": _safe_float(verdict_data.get("confidence", 0.0)),
            "corrected_claim": verdict_data.get("corrected_claim"),
            "primary_url": verdict_data.get("primary_url", "N/A"),
            "evidence_text": evidence_text,
            "evidence_passages": evidence_passages[:3],

            "support_analysis": support_raw,
            "contradiction_analysis": contradiction_raw,
            "support_summary": verdict_data.get("support_summary", ""),
            "contradiction_summary": verdict_data.get("contradiction_summary", ""),
            "deliberation_used": True,
        }

        print(f"\n{'' * 20}")
        print(f"  TRIBUNAL VERDICT: {result['verdict']} (confidence: {result['confidence']})")
        print(f"  Support:       {result.get('support_summary', 'N/A')[:100]}")
        print(f"  Contradiction: {result.get('contradiction_summary', 'N/A')[:100]}")
        print(f"{' ' * 20}\n")

        return result

    except Exception as e:
        print(f"\n[TRIBUNAL ERROR] Adversarial deliberation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def _format_evidence_for_agents(evidence_passages: List[Dict]) -> str:

    if not evidence_passages:
        return "No evidence available."

    lines = []

    for i, ev in enumerate(evidence_passages[:6], 1):
        source = ev.get("source_url", "N/A")
        score = ev.get("score", 0.0)
        content = ev.get("content", "")

        if not isinstance(content, str):
            content = str(content)

        content = content.strip()
        if len(content) > 1000:
            content = content[:1000].rstrip() + "..."

        lines.append(
            f"Evidence {i} [Source: {source}] (Relevance: {score}):\n"
            f"  \"{content}\""
        )

    return "\n\n".join(lines)


def _parse_json_safe(raw: str) -> dict:
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    depth = 0
    start = None

    for i, ch in enumerate(raw):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(raw[start:i + 1])
                except json.JSONDecodeError:
                    pass
                break

    return {}


def _parse_judge_verdict(raw: str) -> dict:

    parsed = _parse_json_safe(raw)

    if parsed and "verdict" in parsed:
        return parsed

    text = raw or ""
    verdict = "NEUTRAL"

    verdict_pattern = re.search(
        r'\b(?:verdict|ruling|decision|conclusion)\b[:\s]+["\']?\b(TRUE|FALSE|NEUTRAL)\b',
        text,
        re.IGNORECASE,
    )

    if verdict_pattern:
        verdict = verdict_pattern.group(1).upper()

    return {
        "verdict": verdict,
        "explanation": text[:500] if text else "Judge output could not be parsed as JSON.",
        "confidence": 0.0,
        "corrected_claim": None,
        "primary_url": "N/A",
        "support_summary": "",
        "contradiction_summary": "",
    }


def _safe_float(value) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(1.0, value))