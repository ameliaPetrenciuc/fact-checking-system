from urllib.parse import urlparse
from typing import List, Dict

from server.ai_client import get_similarity_scores


REFUTATION_TERMS = {
    "false", "no evidence", "cannot", "does not", "myth",
    "misinformation", "fact check", "debunked", "misleading",
    "no scientific", "not supported", "disproven", "incorrect",
    "no proof", "unfounded", "baseless", "unverified", "fabricated",
    "hoax", "rumor", "rumour", "misleads", "exaggerated", "inaccurate",
    "not true", "claim is false", "verdict: false", "rating: false",
    "no cure", "not a cure", "does not cure", "not proven",
    "not approved", "no approved treatment", "not recommended",
    "experts say", "scientists say", "health authorities",
    "there is no evidence", "contrary to claims",
}

STRONG_REFUTATION_PHRASES = {
    "verdict: false", "rating: false", "claim is false",
    "this is false", "this is misleading", "pants on fire",
    "four pinocchios", "no, this is", "fact check: false",
}

REFUTATION_BOOST = 0.04        # standard boost
STRONG_REFUTATION_BOOST = 0.08  # boost for explicit verdict phrases


def extract_relevant_evidence(claim, web_text, top_k=6):
    if not web_text or not isinstance(web_text, (str, list)):
        return []

    if isinstance(web_text, list):
        sentences = [s.strip() for s in web_text if len(s.strip()) > 15]

    elif isinstance(web_text, str):
        raw_sentences = web_text.split('.')
        sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 15]
    else:
        return []

    if not sentences:
        return []

    cosine_scores = get_similarity_scores(claim, sentences)

    scored = sorted(
        zip(cosine_scores, sentences),
        key=lambda x: x[0],
        reverse=True
    )

    results = []
    SIMILARITY_THRESHOLD = 0.40
    for score, sentence in scored[:top_k]:
        score_rounded = round(float(score), 4)

        if score_rounded >= SIMILARITY_THRESHOLD:
            content = sentence
            if not content.endswith('.'):
                content += "."

            results.append({
                "content": content,
                "score": score_rounded
            })

    return results


def diversify_evidence(
    scored_passages: List[Dict],
    max_per_domain: int = 2,
    final_top_k: int = 6
) -> List[Dict]:

    if not scored_passages:
        return []

    for p in scored_passages:
        content_lower = p.get("content", "").lower()
        if any(phrase in content_lower for phrase in STRONG_REFUTATION_PHRASES):
            p["_boosted_score"] = p["score"] + STRONG_REFUTATION_BOOST
        elif any(term in content_lower for term in REFUTATION_TERMS):
            p["_boosted_score"] = p["score"] + REFUTATION_BOOST
        else:
            p["_boosted_score"] = p["score"]

    sorted_passages = sorted(scored_passages, key=lambda x: x["_boosted_score"], reverse=True)

    selected = []
    domain_counts: Dict[str, int] = {}

    for p in sorted_passages:
        domain = _extract_domain(p.get("source_url", ""))
        count = domain_counts.get(domain, 0)

        if count < max_per_domain:
            selected.append(p)
            domain_counts[domain] = count + 1

        if len(selected) >= final_top_k:
            break

    if len(selected) < final_top_k:
        selected_ids = set(id(p) for p in selected)
        for p in sorted_passages:
            if id(p) not in selected_ids:
                selected.append(p)
                if len(selected) >= final_top_k:
                    break

    for p in scored_passages:
        p.pop("_boosted_score", None)

    return selected


def _extract_domain(url: str) -> str:

    if not url or url == "N/A":
        return "unknown"
    try:
        parts = urlparse(url).netloc.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"

