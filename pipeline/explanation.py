def build_memory_response(cached_result):
    strategy = cached_result.get("strategy_used", "Unknown")
    verdict = cached_result.get("verdict", "NEUTRAL")
    base_explanation = cached_result.get("explanation", "")
    matched_text = cached_result.get("matched_text", "N/A")
    source_type = cached_result.get("source_type", "unknown")
    requires_web = cached_result.get("requires_web_verification", True)
    antidotes = cached_result.get("antidotes", [])
    effective_truth = cached_result.get("effective_truth")
    nli_label = cached_result.get("nli_label")
    nli_score = cached_result.get("nli_score", 0.0)
    similarity_score = cached_result.get("similarity_score", 0.0)

    if verdict == "TRUE":
        final_answer = "Afirmația este susținută de baza de cunoștințe."
    elif verdict == "FALSE":
        final_answer = "Afirmația este falsă conform bazei de cunoștințe."
    elif verdict == "SUSPICIOUS":
        final_answer = "Afirmația este suspectă (zvon fără antidot verificat)."
    else:
        final_answer = "Afirmația nu poate fi decisă doar din memorie."

    explanation_lines = [base_explanation]

    if matched_text and matched_text != "N/A":
        explanation_lines.append(f"Dovadă găsită în graf: {matched_text}")

    if antidotes and verdict == "FALSE":
        explanation_lines.append(f"Corecție (antidot): {antidotes[0]}")

    if strategy == "MACRO (Claim)":
        if effective_truth:
            explanation_lines.append(f"Adevăr efectiv în graf: {effective_truth}")
        if nli_label:
            explanation_lines.append(
                f"Relație logică NLI: {nli_label} (scor: {nli_score:.4f})"
            )

    explanation_lines.append(
        f"Sursă internă: {source_type} | Rută: {strategy} | Similaritate: {similarity_score:.4f}"
    )

    full_explanation = "\n".join(explanation_lines)

    evidence_from_kg = {
        "matched_text": matched_text,
        "strategy_used": strategy,
        "source_type": source_type,
        "similarity_score": similarity_score,
        "effective_truth": effective_truth,
        "nli_label": nli_label,
        "nli_score": nli_score,
        "antidote": antidotes[0] if antidotes else None
    }

    return {
        "final_answer": final_answer,
        "explanation": full_explanation,
        "needs_web": requires_web,
        "strategy_used": strategy,
        "verdict": verdict,
        "nli_label": nli_label,
        "nli_score": nli_score,
        "effective_truth": effective_truth,
        "evidence_from_kg": evidence_from_kg
    }

