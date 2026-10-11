import re

from pipeline.decision import get_decision
from pipeline.evidence import get_aggregated_evidence
from pipeline.nlp_utils import extract_relevant_evidence, diversify_evidence
from pipeline.triple_extractor import TripleExtractorAgent
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP
from pipeline.web_search import search_web, filter_trusted_sources
from pipeline.query_optimizer import generate_search_query
from text_processing.chunker import TextChunker


def build_enriched_chunks(scraped_articles, chunk_size, chunk_overlap):
    chunker = TextChunker(chunk_size, chunk_overlap)
    all_enriched_chunks = []

    for article in scraped_articles:
        url = article["url"]
        text = article["content"]

        chunks_data = chunker.chunk_text(text)
        for c in chunks_data:
            enriched_text = f"[Sursă: {url}] {c['text']}"
            all_enriched_chunks.append(enriched_text)

    return all_enriched_chunks


def gather_web_evidence(claim_text):

    print(f"[EVIDENCE] 🔍 Query optimization...")
    optimized_query = generate_search_query(claim_text)
    print(f"[EVIDENCE] Search query: {optimized_query}")

    raw_results = search_web(optimized_query)
    print(f"[EVIDENCE] DuckDuckGo returned {len(raw_results)} raw results.")

    trusted_results = filter_trusted_sources(raw_results)
    print(f"[EVIDENCE] {len(trusted_results)} trusted results after filtering.")

    source_domains, scraped_articles = get_aggregated_evidence(trusted_results)

    if not scraped_articles:
        print("[EVIDENCE] ❌ No text evidence found from trusted sources.")
        return None

    print(f"[EVIDENCE] ✅ Scraped {len(scraped_articles)} articles from: {source_domains}")

    all_enriched_chunks = build_enriched_chunks(scraped_articles, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"[EVIDENCE] SBERT ranking {len(all_enriched_chunks)} chunks...")

    top_evidence = extract_relevant_evidence(claim_text, all_enriched_chunks, top_k=15)

    if not top_evidence:
        print("[EVIDENCE] ❌ Could not extract relevant sentences from scraped content.")
        return None

    evidence_with_urls = []
    for ev in top_evidence:
        content = ev.get("content", "")
        source_url = "N/A"
        url_match = re.match(r'\[Sursă:\s*(https?://[^\]]+)\]\s*(.*)', content, re.DOTALL)
        if url_match:
            source_url = url_match.group(1).strip()
            content = url_match.group(2).strip()

        evidence_with_urls.append({
            "content": content,
            "score": round(float(ev.get("score", 0.0)), 4),
            "source_url": source_url
        })

    evidence_with_urls = diversify_evidence(evidence_with_urls, max_per_domain=3, final_top_k=6)

    print(f"[EVIDENCE] ✅ Returning {len(evidence_with_urls)} diversified evidence passages.")
    for i, ev in enumerate(evidence_with_urls, 1):
        print(f"   [{i}] (Score: {ev['score']}) {ev['source_url'][:60]}")

    return {
        "evidence_passages": evidence_with_urls,
        "evidence_text": "\n".join(e["content"] for e in evidence_with_urls),
        "sources": source_domains.split(", ") if source_domains else [],
        "query_used": optimized_query,
    }


def run_web_investigation(raw_text):
    print(f"[*] (Llama 3.2) extrage cuvinte cheie...")
    optimized_query = generate_search_query(raw_text)
    print(f" [→] Query pentru motor de căutare: {optimized_query}")

    raw_results = search_web(optimized_query)
    print(f"    [DEBUG] DuckDuckGo a găsit {len(raw_results)} rezultate brute.")

    for r in raw_results[:3]:
        print(f"    [DEBUG] Link găsit: {r['link']}")

    trusted_results = filter_trusted_sources(raw_results)
    source_domains, scraped_articles = get_aggregated_evidence(trusted_results)

    if not scraped_articles:
        print("No text evidence found in trusted sources.")
        return None

    print(f"\n{'=' * 50}")
    print(f"👀 AM EXTRAS DATE DE PE: {source_domains}")
    print(f"Total articole valide: {len(scraped_articles)}")
    print(f"{'=' * 50}\n")

    print("Applying Intelligent Chunking with Metadata Injection...")

    all_enriched_chunks = build_enriched_chunks(scraped_articles, CHUNK_SIZE, CHUNK_OVERLAP)

    print(f"SBERT analyzing {len(all_enriched_chunks)} relevant chunks...")
    top_evidence = extract_relevant_evidence(raw_text, all_enriched_chunks, top_k=6)

    if not top_evidence:
        print("Could not extract useful sentences from the scraped text.")
        return None

    print("\nSentences from the article that SBERT found relevant to the claim:")
    for i, ev in enumerate(top_evidence):
        print(f"   [{i + 1}] (Scor: {ev['score']:.4f}) -> {ev['content']}")
    print("-" * 40)

    print(f"\nLLM Agent (Llama 3.2) reads the evidence...")
    llm_decision = get_decision(raw_text, top_evidence)

    best_url = llm_decision.get("primary_url", "N/A")
    corrected_claim = llm_decision.get("corrected_claim")

    print(f"\n{'=' * 20} VERDICT AGENT LLM {'=' * 20}")
    print(f"VERDICT   : {llm_decision.get('verdict', 'NEUTRAL')}")
    print(f"EXPLICAȚIE: {llm_decision.get('explanation', 'N/A')}")
    print(f"CLAIM CORECTAT: {corrected_claim}")
    print(f"SURSĂ BAZĂ: {best_url}")
    print(f"CONFIDENȚĂ: {llm_decision.get('confidence', 'N/A')}")
    print(f"{'=' * 59}\n")

    verdict = llm_decision.get("verdict", "NEUTRAL")
    if verdict not in ["TRUE", "FALSE", "NEUTRAL"]:
        verdict = "NEUTRAL"

    return {
        "verdict": verdict,
        "explanation": llm_decision.get("explanation", "N/A"),
        "primary_url": best_url,
        "confidence": llm_decision.get("confidence", 0.0),
        "corrected_claim": corrected_claim,
        "evidence_text": "\n".join([ev.get("content", "") for ev in top_evidence]),
        "evidence_passages": [
        {
            "source_url": ev.get("source_url") or ev.get("url") or "N/A",
            "content": ev.get("content", ""),
            "score": ev.get("score", 0.0)
        }
        for ev in top_evidence[:3]
    ]
    }


def run_ontology_extraction(claim_text, web_result):

    extractor = TripleExtractorAgent()
    evidence_passages = web_result.get("evidence_passages", [])
    if evidence_passages:
        evidence_text = "\n".join(
            [p.get("content", "") for p in evidence_passages if p.get("content")]
        )
    else:
        evidence_text = web_result.get("evidence_text", "")

    live_triples = extractor.extract_live_triples(
        claim_text=claim_text,
        verdict=web_result.get("verdict", "NEUTRAL"),
        explanation=web_result.get("explanation", ""),
        evidence_text=evidence_text,
        corrected_claim=web_result.get("corrected_claim", "")
    )

    verified_triples = live_triples.get("verified_triples", [])

    print(f"VERIFIED TRIPLES: {len(verified_triples)}")
    for t in verified_triples:
        print(f"   [V] ({t['subject']}) --[{t['predicate']}]--> ({t['object']})")
    print(f"{'=' * 60}\n")

    return verified_triples


def resolve_web_persistence_plan(user_text, web_result):
    verdict = web_result.get("verdict", "NEUTRAL")
    corrected_claim = web_result.get("corrected_claim")

    if verdict == "TRUE":
        return {
            "mode": "store_true_only",
            "false_claim_text": None,
            "true_claim_text": user_text
        }

    if verdict == "FALSE" and corrected_claim:
        return {
            "mode": "store_false_and_corrected",
            "false_claim_text": user_text,
            "true_claim_text": corrected_claim
        }

    return {
        "mode": "store_nothing",
        "false_claim_text": None,
        "true_claim_text": None
    }



