from pipeline.nli import check_claim_relation
from server.ai_client import get_embedding
from config.settings import (
    KG_CANDIDATE_THRESHOLD,
    HIGH_SIMILARITY_THRESHOLD,
    SHORT_QUERY_WORD_LIMIT,
    MICRO_PREFERENCE_GAP,
    LOW_CONFIDENCE_THRESHOLD,
    NEUTRAL_CONFIDENCE_THRESHOLD,
    NEUTRAL_NLI_MIN_SIMILARITY
)
from pipeline.scoring import compute_internal_confidence, compute_graph_support_score
import re

def resolve_claim_truth(claim_record):
    verdict = claim_record.get("verdict")
    label = claim_record.get("label")

    if verdict in ("TRUE", "FALSE"):
        return verdict

    if label == "real":
        return "TRUE"

    if label == "fake":
        return "FALSE"

    return None

def _is_highly_similar_template(text_a: str, text_b: str, similarity_threshold: float = 0.55) -> bool:

    num_pattern = re.compile(r'\d[\d,\.]*')
    clean_a = num_pattern.sub('', text_a.lower())
    clean_b = num_pattern.sub('', text_b.lower())

    clean_a = re.sub(r'[^\w\s]', '', clean_a).strip()
    clean_b = re.sub(r'[^\w\s]', '', clean_b).strip()

    # Jaccard similarity on word sets (order-independent)
    words_a = set(clean_a.split())
    words_b = set(clean_b.split())

    if not words_a or not words_b:
        return False

    intersection = words_a & words_b
    union = words_a | words_b
    jaccard = len(intersection) / len(union)

    return jaccard >= similarity_threshold


def create_vector_indexes(tx):
    # 1. Indexul pentru Texte Lungi (Paragrafe/Știri întregi)
    query_claims = """
    CREATE VECTOR INDEX claim_embeddings IF NOT EXISTS
    FOR (c:Claim) ON (c.embedding)
    OPTIONS {indexConfig: {
     `vector.dimensions`: 768,
     `vector.similarity_function`: 'cosine'
    }}
    """
    print("aici")

    # 2. Indexul pentru Întrebări Scurte și Zvonuri Atomice
    query_facts = """
    CREATE VECTOR INDEX fact_embeddings IF NOT EXISTS
    FOR (f:Fact) ON (f.embedding)
    OPTIONS {indexConfig: {
     `vector.dimensions`: 768,
     `vector.similarity_function`: 'cosine'
    }}
    """

    try:
        tx.run(query_claims)
        print("[✓] Index 'claim_embeddings' activat (pentru texte lungi).")
        tx.run(query_facts)
        print("[✓] Index 'fact_embeddings' activat (pentru interogări punctuale).")
    except Exception as e:
        print(f"[!] Eroare la crearea indexurilor: {e}")


def find_best_semantic_match(tx, user_text, similarity_threshold=KG_CANDIDATE_THRESHOLD):
    query_vector = get_embedding(user_text)

    # RUTA 1: MACRO SEARCH - Claim-uri lungi
    query_macro = """
        CYPHER 25

        MATCH (claim)
          SEARCH claim IN (
            VECTOR INDEX claim_embeddings
            FOR $query_vector
            LIMIT 1
          ) SCORE AS score

        WHERE score >= $threshold

        RETURN claim.text AS text,
               claim.label AS label,
               claim.verdict AS verdict,
               claim.source_type AS source_type,
               claim.explanation AS explanation,
               claim.source_url AS source_url,
               score
        """
    res_macro = tx.run(
        query_macro,
        query_vector=query_vector,
        threshold=similarity_threshold
    ).single()

    # RUTA 2: MICRO SEARCH - Facts
    query_micro = """
        CYPHER 25

        MATCH (f)
          SEARCH f IN (
            VECTOR INDEX fact_embeddings
            FOR $query_vector
            LIMIT 1
          ) SCORE AS score

        WHERE score >= $threshold

        OPTIONAL MATCH (f)-[:ABOUT]->(e:Entity)
        OPTIONAL MATCH (e)<-[:ABOUT]-(antidote:VerifiedFact)
        WHERE antidote IS NULL OR antidote <> f

        RETURN f.text AS matched_text,
               f.truth_status AS truth_status,
               labels(f) AS labels,
               collect(DISTINCT antidote.text) AS antidotes,
               f.source_type AS source_type,
               f.source_url AS source_url,
               score
        LIMIT 1
        """
    res_micro = tx.run(
        query_micro,
        query_vector=query_vector,
        threshold=similarity_threshold
    ).single()

    # SCORURI
    score_macro = res_macro["score"] if res_macro else 0
    score_micro = res_micro["score"] if res_micro else 0

    print(f"[DEBUG] MACRO score: {score_macro}")
    print(f"[DEBUG] MICRO score: {score_micro}")

    macro_eligible = score_macro >= similarity_threshold
    micro_eligible = score_micro >= similarity_threshold

    if not macro_eligible and not micro_eligible:
        return None

    # ARBITRAJ MACRO vs MICRO
    if macro_eligible and not micro_eligible:
        winner = "MACRO"
    elif micro_eligible and not macro_eligible:
        winner = "MICRO"
    else:
        score_gap = abs(score_macro - score_micro)
        word_count = len(user_text.split())

        prefer_micro = (
            word_count <= SHORT_QUERY_WORD_LIMIT
            and score_gap <= MICRO_PREFERENCE_GAP
        )

        if word_count > SHORT_QUERY_WORD_LIMIT and macro_eligible:
            winner = "MACRO" if (score_micro - score_macro) <= 0.05 else "MICRO"
        elif prefer_micro:
            winner = "MICRO"
        else:
            winner = "MACRO" if score_macro >= score_micro else "MICRO"

        print(
            f"[DEBUG] Arbitration: winner={winner}, "
            f"word_count={word_count}, score_gap={score_gap:.4f}, "
            f"prefer_micro={prefer_micro}"
        )

    # CAZ MACRO — Claim-level reasoning
    if winner == "MACRO":
        relation = check_claim_relation(
            premise=res_macro["text"],
            hypothesis=user_text
        )

        nli_label = relation["label"].upper()
        nli_score = relation["score"]
        all_scores = relation.get("all_scores", {})
        effective_truth = resolve_claim_truth(res_macro)

        graph_support = compute_graph_support_score(
            tx,
            res_macro["text"],
            "MACRO"
        )

        confidence = compute_internal_confidence(
            similarity_score=score_macro,
            nli_scores=all_scores,
            graph_support_score=graph_support
        )

        print(f"[DEBUG] MACRO NLI: {nli_label} (score: {nli_score:.4f})")
        print(f"[DEBUG] MACRO graph support: {graph_support}")
        print(f"[DEBUG] MACRO internal confidence: {confidence}")

        if (
                0.85 <= score_macro < 0.98
                and _is_highly_similar_template(res_macro["text"], user_text)
                and nli_label == "CONTRADICTION"
        ):
            nli_label = "NEUTRAL"
            nli_score = 0.50
            confidence = 0.50
            print("[DEBUG] 🛡️ Numeric guard: → NEUTRAL (same template, different numbers)")

        base_result = {
            "strategy_used": "MACRO (Claim)",
            "matched_text": res_macro["text"],
            "source_url": res_macro["source_url"],
            "source_type": res_macro["source_type"],
            "similarity_score": score_macro,
            "nli_label": nli_label,
            "nli_score": nli_score,
            "nli_scores": all_scores,
            "effective_truth": effective_truth,
            "internal_confidence": confidence,
            "graph_support_score": graph_support,
            "antidotes": [],
        }

        # A. NLI are direcție clară
        if nli_label in ("ENTAILMENT", "CONTRADICTION"):
            if nli_label == "ENTAILMENT":
                if effective_truth == "TRUE":
                    verdict = "TRUE"
                elif effective_truth == "FALSE":
                    verdict = "FALSE"
                else:
                    verdict = "NEUTRAL"

            else:  # CONTRADICTION
                if score_macro < 0.93:
                    verdict = "NEUTRAL"
                    requires_web = True
                    explanation = (
                        f"NLI indică CONTRADICTION, dar similaritatea ({score_macro:.2f}) "
                        f"este prea scăzută pentru a inversa verdictul din Knowledge Graph."
                    )
                    return {
                        **base_result,
                        "verdict": verdict,
                        "explanation": explanation,
                        "requires_web_verification": requires_web,
                    }
                elif effective_truth == "TRUE":
                    verdict = "FALSE"
                elif effective_truth == "FALSE":
                    verdict = "TRUE"
                else:
                    verdict = "NEUTRAL"

            if verdict != "NEUTRAL" and confidence >= LOW_CONFIDENCE_THRESHOLD:
                requires_web = False
                explanation = (
                    f"NLI ({nli_label}) oferă o direcție logică clară, "
                    f"iar scorul compus ({confidence:.2f}) este suficient "
                    f"pentru a răspunde din Knowledge Graph."
                )
            else:
                verdict = "NEUTRAL"
                requires_web = True
                explanation = (
                    f"NLI ({nli_label}) indică o direcție, dar scorul compus "
                    f"({confidence:.2f}) nu este suficient pentru a decide doar din Knowledge Graph."
                )

        # B. NLI = NEUTRAL
        else:
            # HIGH-NEUTRAL GUARD: overwhelmingly NEUTRAL (>0.95) means premise and
            # hypothesis are about different topics despite shared keywords → web fallback.
            if nli_score >= 0.95:
                verdict = "NEUTRAL"
                requires_web = True
                explanation = (
                    f"NLI este puternic NEUTRAL ({nli_score:.2f}), indicând că "
                    f"afirmația din graf și interogarea nu au aceeași semnificație logică, "
                    f"chiar dacă vocabularul se suprapune (similaritate {score_macro:.2f}). "
                    f"Este necesară verificarea pe web."
                )
            elif (
                    effective_truth in ("TRUE", "FALSE")
                    and confidence >= NEUTRAL_CONFIDENCE_THRESHOLD
                    and score_macro >= NEUTRAL_NLI_MIN_SIMILARITY
            ):
                verdict = effective_truth
                requires_web = False
                explanation = (
                    f"NLI este NEUTRAL, deci relația logică nu este clară, "
                    f"dar similaritatea semantică ({score_macro:.2f}) și suportul grafului "
                    f"({graph_support:.2f}) duc la un scor compus suficient "
                    f"({confidence:.2f}). Sistemul tratează afirmația ca o parafrazare "
                    f"a cunoașterii existente în KG."
                )
            else:
                verdict = "NEUTRAL"
                requires_web = True
                if score_macro < NEUTRAL_NLI_MIN_SIMILARITY:
                    explanation = (
                        f"NLI este NEUTRAL și similaritatea ({score_macro:.2f}) este sub pragul "
                        f"minim ({NEUTRAL_NLI_MIN_SIMILARITY}) pentru inferență directă din KG. "
                        f"Este necesară verificarea pe web."
                    )
                else:
                    explanation = (
                        f"NLI este NEUTRAL, iar scorul compus ({confidence:.2f}) "
                        f"nu este suficient pentru a decide din Knowledge Graph. "
                        f"Este necesară verificarea pe web."
                    )

        return {
            **base_result,
            "verdict": verdict,
            "explanation": explanation,
            "requires_web_verification": requires_web,
        }

    # CAZ MICRO — Fact-level reasoning with NLI + Graph Support
    labels = res_micro["labels"] or []
    antidotes = [a for a in (res_micro["antidotes"] or []) if a]

    graph_support_micro = compute_graph_support_score(
        tx,
        res_micro["matched_text"],
        "MICRO"
    )

    relation = check_claim_relation(
        premise=res_micro["matched_text"],
        hypothesis=user_text
    )

    nli_label = relation["label"].upper()
    nli_score = relation["score"]
    all_scores = relation.get("all_scores", {})

    confidence = compute_internal_confidence(
        similarity_score=score_micro,
        nli_scores=all_scores,
        graph_support_score=graph_support_micro
    )

    print(f"[DEBUG] MICRO NLI: {nli_label} (score: {nli_score:.4f})")
    print(f"[DEBUG] MICRO graph support: {graph_support_micro}")
    print(f"[DEBUG] MICRO internal confidence: {confidence}")

    base_micro = {
        "strategy_used": "MICRO (Fact)",
        "matched_text": res_micro["matched_text"],
        "source_type": res_micro["source_type"],
        "source_url": res_micro["source_url"],
        "similarity_score": score_micro,
        "nli_label": nli_label,
        "nli_score": nli_score,
        "nli_scores": all_scores,
        "graph_support_score": graph_support_micro,
        "internal_confidence": confidence,
    }

    # 1. Matched node is VerifiedFact
    if "VerifiedFact" in labels:

        if nli_label == "ENTAILMENT":
            if confidence >= LOW_CONFIDENCE_THRESHOLD:
                return {
                    **base_micro,
                    "verdict": "TRUE",
                    "explanation": (
                        "Afirmația este susținută de un fapt verificat din Knowledge Graph, "
                        f"iar scorul compus ({confidence:.2f}) este suficient."
                    ),
                    "antidotes": [],
                    "requires_web_verification": False
                }

            return {
                **base_micro,
                "verdict": "NEUTRAL",
                "explanation": (
                    "Afirmația pare susținută de un fapt verificat, dar scorul compus "
                    f"({confidence:.2f}) este prea mic pentru a decide doar din KG."
                ),
                "antidotes": [],
                "requires_web_verification": True
            }

        elif nli_label == "CONTRADICTION":
            # Guard: similarity too low to trust CONTRADICTION for a different entity
            # e.g. "Boris Johnson tested positive" should NOT invert "Trump tested positive"
            if score_micro < 0.90:
                return {
                    **base_micro,
                    "verdict": "NEUTRAL",
                    "explanation": (
                        f"MICRO CONTRADICTION detectat, dar similaritatea ({score_micro:.2f}) "
                        f"este prea scăzută pentru a inversa un fapt verificat. "
                        f"Posibil mismatch de entitate → web fallback."
                    ),
                    "antidotes": [],
                    "requires_web_verification": True
                }
            if confidence >= LOW_CONFIDENCE_THRESHOLD:
                return {
                    **base_micro,
                    "verdict": "FALSE",
                    "explanation": (
                        "Afirmația contrazice un fapt verificat din Knowledge Graph, "
                        f"iar scorul compus ({confidence:.2f}) este suficient."
                    ),
                    "antidotes": [res_micro["matched_text"]],
                    "requires_web_verification": False
                }

            return {
                **base_micro,
                "verdict": "NEUTRAL",
                "explanation": (
                    "Afirmația pare să contrazică un fapt verificat, dar scorul compus "
                    f"({confidence:.2f}) este prea mic pentru a decide doar din KG."
                ),
                "antidotes": [res_micro["matched_text"]],
                "requires_web_verification": True
            }

        else:
            # NLI = NEUTRAL
            if confidence >= NEUTRAL_CONFIDENCE_THRESHOLD:
                return {
                    **base_micro,
                    "verdict": "TRUE",
                    "explanation": (
                        "NLI nu a identificat clar relația logică, dar afirmația este foarte "
                        "apropiată semantic de un fapt verificat, iar scorul compus indică "
                        f"suport suficient în graf ({confidence:.2f})."
                    ),
                    "antidotes": [],
                    "requires_web_verification": False
                }

            return {
                **base_micro,
                "verdict": "NEUTRAL",
                "explanation": (
                    "A fost găsit un fapt verificat similar, dar relația logică este neclară "
                    f"și scorul compus ({confidence:.2f}) nu este suficient pentru a decide "
                    "doar din Knowledge Graph."
                ),
                "antidotes": [],
                "requires_web_verification": True
            }

    # 2. Matched node is ClaimedFact
    if "ClaimedFact" in labels:

        if antidotes:
            if nli_label == "ENTAILMENT":
                return {
                    **base_micro,
                    "verdict": "FALSE",
                    "explanation": (
                        f"Afirmația reproduce o dezinformare cunoscută. "
                        f"Corecția verificată este: {antidotes[0]}"
                    ),
                    "antidotes": antidotes,
                    "requires_web_verification": False
                }

            elif nli_label == "CONTRADICTION":
                # Guard: similarity too low — may be a different entity
                # e.g. "Boris Johnson tested positive" should NOT invert "Trump tested positive"
                if score_micro < 0.90:
                    return {
                        **base_micro,
                        "verdict": "NEUTRAL",
                        "explanation": (
                            f"MICRO CONTRADICTION pe ClaimedFact, similaritate ({score_micro:.2f}) "
                            f"insuficientă → posibil entitate diferită. Web fallback."
                        ),
                        "antidotes": antidotes,
                        "requires_web_verification": True
                    }
                return {
                    **base_micro,
                    "verdict": "TRUE",
                    "explanation": (
                        f"Afirmația contrazice o dezinformare cunoscută. "
                        f"Corecția verificată din graf este: {antidotes[0]}"
                    ),
                    "antidotes": antidotes,
                    "requires_web_verification": False
                }

            else:
                return {
                    **base_micro,
                    "verdict": "SUSPICIOUS",
                    "explanation": (
                        "Afirmația este similară cu un zvon cunoscut, iar graful conține "
                        "o corecție verificată, dar relația logică nu este suficient de clară. "
                        "Este necesară verificarea pe web."
                    ),
                    "antidotes": antidotes,
                    "requires_web_verification": True
                }

        return {
            **base_micro,
            "verdict": "SUSPICIOUS",
            "explanation": (
                "Afirmația a fost găsită în graf ca posibil zvon, dar nu există încă "
                "un antidot verificat asociat. Este necesară verificarea pe web."
            ),
            "antidotes": [],
            "requires_web_verification": True
        }

    return None

