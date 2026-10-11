# ── MACRO scoring weights ──
_MACRO_WEIGHT_VERIFIED = 0.55    # Verified facts directly justifying the claim
_MACRO_WEIGHT_ENTITIES = 0.30    # Entities connected through verified facts
_MACRO_WEIGHT_CORRECTED = 0.15   # Bonus: claim has a CORRECTED_BY link

# ── MICRO scoring weights (VerifiedFact path) ──
_MICRO_VERIFIED_WEIGHT_DIRECT = 0.45
_MICRO_VERIFIED_WEIGHT_CORROBORATING = 0.30
_MICRO_VERIFIED_WEIGHT_ENTITIES = 0.25

# ── MICRO scoring weights (ClaimedFact-with-antidotes path) ──
_MICRO_CLAIMED_WEIGHT_ANTIDOTES = 0.70
_MICRO_CLAIMED_WEIGHT_ENTITIES = 0.30      # Entity coverage

# ── Normalization caps ──
_MAX_VERIFIED_FACTS = 2
_MAX_ENTITIES = 2
_MAX_CORROBORATING = 2

# ── Composite confidence weights ──
_CONFIDENCE_WEIGHT_SBERT = 0.60       # Retrieval quality
_CONFIDENCE_WEIGHT_NLI = 0.30         # Directional reasoning strength
_CONFIDENCE_WEIGHT_GRAPH = 0.10       # Structural evidence density


def compute_graph_support_score(tx, matched_text: str, strategy: str) -> float:
    """
    Queries Neo4j to measure structural evidence density
    around the matched claim or fact node.

    Signal hierarchy:
      JUSTIFIED_BY → VerifiedFact    = STRONG (direct evidence)
      ABOUT → Entity (from facts)    = MODERATE (structural integration)
      CORRECTED_BY → Claim           = BONUS (misinformation was addressed)
      CLAIMS_ENTITY → Entity         = IGNORED (noisy)
    """
    if strategy == "MACRO":
        result = tx.run("""
            MATCH (c:Claim {text: $text})
            OPTIONAL MATCH (c)-[:JUSTIFIED_BY]->(vf:VerifiedFact)
            OPTIONAL MATCH (c)-[:ASSERTS]->(cf:ClaimedFact)
            OPTIONAL MATCH (c)-[:CORRECTED_BY]->(corrected:Claim)
            OPTIONAL MATCH (vf)-[:ABOUT]->(e1:Entity)
            OPTIONAL MATCH (cf)-[:ABOUT]->(e2:Entity)
            WITH count(DISTINCT vf) + count(DISTINCT cf) AS fact_count,
                 count(DISTINCT corrected) AS corrected_count,
                 count(DISTINCT e1) + count(DISTINCT e2) AS entity_count
            RETURN fact_count AS verified_count,
                   corrected_count,
                   entity_count
        """, text=matched_text).single()

        if not result:
            return 0.0

        verified = min((result["verified_count"] or 0), _MAX_VERIFIED_FACTS) / _MAX_VERIFIED_FACTS
        entities = min((result["entity_count"] or 0), _MAX_ENTITIES) / _MAX_ENTITIES
        corrected = 1.0 if (result["corrected_count"] or 0) > 0 else 0.0

        return round(
            _MACRO_WEIGHT_VERIFIED * verified +
            _MACRO_WEIGHT_ENTITIES * entities +
            _MACRO_WEIGHT_CORRECTED * corrected,
            4
        )

    else:  # MICRO
        result = tx.run("""
            MATCH (f:Fact {text: $text})
            OPTIONAL MATCH (f)-[:ABOUT]->(e:Entity)
            OPTIONAL MATCH (e)<-[:ABOUT]-(other:VerifiedFact)
            WHERE other IS NULL OR other.text <> $text
            RETURN labels(f) AS matched_labels,
                   count(DISTINCT e) AS entity_count,
                   count(DISTINCT other) AS corroborating_verified_count
        """, text=matched_text).single()

        if not result:
            return 0.0

        labels = result["matched_labels"] or []
        corroborating = result["corroborating_verified_count"] or 0
        entity_count = result["entity_count"] or 0

        entities = min(entity_count, _MAX_ENTITIES) / _MAX_ENTITIES

        if "VerifiedFact" not in labels:
            # ClaimedFact with no verified corroboration = zero support
            if corroborating == 0:
                return 0.0
            # ClaimedFact with verified antidotes nearby — partial credit
            verified = min(corroborating, _MAX_CORROBORATING) / _MAX_CORROBORATING
            return round(
                _MICRO_CLAIMED_WEIGHT_ANTIDOTES * verified +
                _MICRO_CLAIMED_WEIGHT_ENTITIES * entities,
                4
            )

        # VerifiedFact — direct verified evidence + neighborhood support
        direct_verified = 1.0
        verified = min(corroborating, _MAX_VERIFIED_FACTS) / _MAX_VERIFIED_FACTS

        return round(
            _MICRO_VERIFIED_WEIGHT_DIRECT * direct_verified +
            _MICRO_VERIFIED_WEIGHT_CORROBORATING * verified +
            _MICRO_VERIFIED_WEIGHT_ENTITIES * entities,
            4
        )


def compute_internal_confidence(
    similarity_score: float,
    nli_scores: dict,
    graph_support_score: float
) -> float:
    """
    Composite confidence from three independent signals:
      SBERT similarity (60%) — retrieval quality
      NLI confidence (30%) — directional reasoning strength
      Graph support (10%) — structural evidence density
    """
    entailment_score = nli_scores.get("entailment", 0.0)
    contradiction_score = nli_scores.get("contradiction", 0.0)
    nli_confidence = max(entailment_score, contradiction_score)

    return round(
        _CONFIDENCE_WEIGHT_SBERT * similarity_score +
        _CONFIDENCE_WEIGHT_NLI * nli_confidence +
        _CONFIDENCE_WEIGHT_GRAPH * graph_support_score,
        4
    )