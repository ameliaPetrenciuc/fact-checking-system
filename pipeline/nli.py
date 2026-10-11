from server.ai_client import get_nli_result


def check_claim_relation(premise: str, hypothesis: str) -> dict:
    result = get_nli_result(premise, hypothesis)

    if result is None:
        raise ConnectionError("NLI server unavailable")

    scores_list = result.get("scores", [])

    if not scores_list:
        raise ValueError(f"Empty NLI response: {result}")

    print("\n===== NLI DEBUG =====")
    print(f"Premise: {premise}")
    print(f"Hypothesis: {hypothesis}")
    print("Scores:")
    for item in scores_list:
        print(f"  {item['label']}: {item['score']:.4f}")
    print("=====================\n")

    top = max(scores_list, key=lambda x: x["score"])

    return {
        "label": top["label"],
        "score": top["score"],
        "all_scores": {item["label"].lower(): item["score"] for item in scores_list}
    }

