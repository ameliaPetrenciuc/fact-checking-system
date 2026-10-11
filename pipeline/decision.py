import json
import os
from openai import OpenAI

TOGETHER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"


def get_decision(claim, evidence_list):
    if not evidence_list:
        return {
            "verdict": "NEUTRAL",
            "explanation": "No relevant evidence was found during the web search process.",
            "confidence": 0.0,
            "primary_url": "N/A",
            "corrected_claim": None
        }

    formatted_evidence = ""
    for i, ev in enumerate(evidence_list):
        content = ev.get('content', 'No content')
        score = ev.get('score', 0)
        source = ev.get('source_url', ev.get('url', 'N/A'))
        formatted_evidence += (
            f"Evidence {i + 1} [Source: {source}] "
            f"(Relevance Score: {score}): {content}\n"
        )

    try:
        client = OpenAI(
            base_url="https://api.together.xyz/v1",
            api_key=os.getenv("TOGETHER_API_KEY"),
        )
    except Exception as e:
        print(f"❌ Eroare la inițializarea clientului LLM: {e}. Ai setat TOGETHER_API_KEY?")
        return {"verdict": "ERROR", "explanation": "Missing API Key", "confidence": 0.0}

    system_prompt = """
    SYSTEM ROLE: You are a strict Logical Fact-Checking Auditor. Your task is to verify a CLAIM by performing a precise semantic and logical comparison with the provided EVIDENCE.

    INSTRUCTIONS:
    1. LOGICAL ANALYSIS: Pay extreme attention to logical operators like "OR", "AND", "IF", and "UNLESS".
       - Example: If evidence says "If you are X OR Y, then do Z", and the claim says "If you are X, do Z", the verdict is SUPPORTED.
    2. FACTUAL MATCHING: Check if specific conditions in the claim are addressed in the evidence. Do not give a NEUTRAL verdict just because the text is long; look for the core condition.
    3. COMPOUND CLAIMS: If the claim contains multiple distinct factual statements, evaluate ALL of them.
       If the evidence confirms the PRIMARY/MOST SPECIFIC assertion but lacks information on a secondary
       generic subpoint, you MAY still return TRUE or FALSE based on the primary assertion.
       Use NEUTRAL only if the unconfirmed subpoint is itself a central factual claim, not background context.
    4. TEMPORAL & QUANTITATIVE LOGIC: When comparing numbers or amounts, do not just say they are "close". Use threshold logic. If a historical claim says "we raised $200M" and evidence says "we raised $256M", the claim is SUPPORTED because the initial threshold was met over time.
    5. VERDICT RULES:
       - TRUE: The evidence directly and explicitly confirms the claim's core assertion. Minor contradictions from earlier or smaller studies do NOT prevent TRUE if a larger or more authoritative source confirms the claim.
       - FALSE: The STRONGEST available evidence clearly and DIRECTLY refutes the claim, OR a credible fact-checker explicitly debunks it. The evidence must explicitly state the opposite — not just fail to confirm.
       - NEUTRAL: The evidence is about the topic but does NOT directly verify or refute the specific assertion. Use NEUTRAL when evidence is off-topic, indirectly related, or discusses the general subject without addressing the exact claim.
    6A. MAGNITUDE / QUALIFIER RULE:
       If the claim contains a qualifier such as "moderate", "modest", "strong", "weak", "low", "high",
       "significant", "limited", "mild", "severe", "substantial", or "robust", the evidence must explicitly
       support that qualifier or provide an equivalent quantitative/contextual measure.
       Evidence that only confirms the general phenomenon is NOT enough for TRUE.
       Example: evidence that a vaccine induces an immune response does NOT verify the claim that it induces
       a moderate immune response unless "moderate" or an equivalent magnitude is supported.
       If the qualifier is not verified, choose NEUTRAL unless the evidence directly refutes it.
    6B. CONDITIONAL SUPPORT RULE:
       If the evidence supports the claim only under specific conditions such as early treatment, late treatment,
       hospitalized patients, severe disease, mild disease, animal models, in vitro experiments, specific dosage,
       timing of administration, or a specific subgroup, do NOT return TRUE for a broader claim unless the claim
       includes the same condition.
       If the evidence is condition-specific and the claim is broader, choose NEUTRAL unless the broader claim
       is directly confirmed.
    7. RELATEDNESS IS NOT CONFIRMATION: If evidence says two entities are "related", "homologous", or "similar", this does NOT confirm they are "different" or "the same". Only use TRUE if the evidence EXPLICITLY states the exact relationship claimed.
    8. NUANCE MATTERS:
       Many scientific claims use hedging language ("may help", "is associated with", 
       "suggests"). If the claim uses cautious language AND the evidence confirms the same finding with 
       the same key conditions, verdict is TRUE. Caveats do not make a hedged claim false. However, if the 
       evidence only supports a narrower, condition-specific, or partial version of the claim, choose NEUTRAL.
    9. MIXED EVIDENCE → TRUE (not FALSE): When multiple sources report contradictory results and AT LEAST ONE large-scale or authoritative source confirms the claim, verdict is TRUE. Early negative studies do NOT override later confirmatory evidence.
    10. DEBUNKING SIGNAL: If a fact-checker (snopes.com, factcheck.org, fullfact.org, boomlive.in, leadstories.com) explicitly states the SPECIFIC claim is "debunked", "refuted", or "found false", treat that as strong contradiction. Verify the debunked claim matches YOUR claim — fact-checkers often debunk a DIFFERENT version.
    11. Provide a brief explanation of your reasoning (2-3 sentences).
    12. Provide a confidence score between 0.0 and 1.0.
    13. CORRECTED CLAIM RULES (CRITICAL ACADEMIC CONSTRAINT):
       - If the verdict is FALSE, you MUST generate a corrected_claim.
       - It MUST be a single, direct, atomic declarative assertion.
       - FORBIDDEN: "there is no evidence that...", "studies show...", "according to...", "research suggests..."
       - BAD: "There is no scientific proof that garlic cures COVID-19."
       - GOOD: "Garlic does not cure COVID-19."
    14. If the verdict is TRUE, set corrected_claim equal to the original claim, cleaned of conversational filler.
    15. If the verdict is NEUTRAL, set corrected_claim to null.

    OUTPUT FORMAT:
    You MUST reply with a valid JSON object ONLY.
    Return the keys in this EXACT order:
    1. "explanation"
    2. "verdict"
    3. "confidence"
    4. "primary_url"
    5. "corrected_claim"

    EXAMPLE OUTPUT:
    {
      "explanation": "The claim is contradicted by the evidence because the cited person explicitly denied making the statement.",
      "verdict": "FALSE",
      "confidence": 0.98,
      "primary_url": "https://example.com/fact-check",
      "corrected_claim": "Tasuku Honjo did not say the coronavirus is not natural."
    }
    """

    user_prompt = f"CLAIM: \"{claim}\"\n\nEVIDENCE FOUND ON TRUSTED WEBSITES:\n{formatted_evidence}"

    try:
        response = client.chat.completions.create(
            model=TOGETHER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        full_content = response.choices[0].message.content
        result = json.loads(full_content)
        raw_verdict = str(result.get("verdict", "NEUTRAL")).upper().strip()
        # Map partial-support aliases to TRUE; anything else unknown → NEUTRAL
        _VERDICT_MAP = {
            "TRUE": "TRUE",
            "FALSE": "FALSE",
            "NEUTRAL": "NEUTRAL",
            "PARTIALLY_SUPPORTED": "TRUE",
            "PARTIALLY SUPPORTED": "TRUE",
            "SUPPORTED": "TRUE",
            "UNSUPPORTED": "NEUTRAL",
        }
        result["verdict"] = _VERDICT_MAP.get(raw_verdict, "NEUTRAL")

        # Normalizare minimă pentru siguranță
        result.setdefault("corrected_claim", None)
        result.setdefault("primary_url", "N/A")
        result.setdefault("confidence", 0.0)
        result.setdefault("explanation", "No explanation returned by model.")

        return result

    except json.JSONDecodeError as e:
        print(f"❌ Eroare parsare JSON de la LLM: {e}. Text: {full_content}")
        return {
            "verdict": "ERROR",
            "explanation": f"JSON parsing error: {str(e)}",
            "confidence": 0.0,
            "primary_url": "N/A",
            "corrected_claim": None
        }

    except Exception as e:
        print(f" Error with LLM communication: {e}")
        return {
            "verdict": "ERROR",
            "explanation": f"JSON parsing error: {str(e)}",
            "confidence": 0.0,
            "primary_url": "N/A",
            "corrected_claim": None
        }