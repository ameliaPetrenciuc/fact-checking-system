import os
from typing import List, Optional

import requests

API_URL = os.getenv(
    "ML_API_URL",
    "http://localhost:8000",
).rstrip("/")

DEFAULT_TIMEOUT = 30
BATCH_READ_TIMEOUT = 300
CONNECT_TIMEOUT = 10


def get_embedding(
    text: str,
    model: str = "all-mpnet-base-v2",
) -> list:
    try:
        response = requests.post(
            f"{API_URL}/get_embedding",
            json={"text": text, "model": model},
            timeout=(CONNECT_TIMEOUT, DEFAULT_TIMEOUT),
        )
        response.raise_for_status()
        return response.json()["embedding"]

    except requests.exceptions.RequestException as e:
        print(f"[!] Embedding server error: {e}")
        return []


def get_embeddings_batch(
    texts: List[str],
    model: str = "all-mpnet-base-v2",
) -> List[list]:
    try:
        response = requests.post(
            f"{API_URL}/get_embeddings_batch",
            json={"texts": texts, "model": model},
            timeout=(CONNECT_TIMEOUT, BATCH_READ_TIMEOUT),
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    except requests.exceptions.RequestException as e:
        print(f"[!] Batch embedding server error: {e}")
        return [[] for _ in texts]


def get_similarity_scores(
    claim: str,
    sentences: List[str],
) -> List[float]:
    try:
        response = requests.post(
            f"{API_URL}/get_similarity",
            json={
                "claim": claim,
                "sentences": sentences,
            },
            timeout=(CONNECT_TIMEOUT, BATCH_READ_TIMEOUT),
        )
        response.raise_for_status()
        return response.json()["scores"]

    except requests.exceptions.RequestException as e:
        print(f"[!] Similarity server error: {e}")
        return [0.0] * len(sentences)


def get_nli_result(
    premise: str,
    hypothesis: str,
) -> Optional[dict]:
    try:
        response = requests.post(
            f"{API_URL}/check_nli",
            json={
                "premise": premise,
                "hypothesis": hypothesis,
            },
            timeout=(CONNECT_TIMEOUT, DEFAULT_TIMEOUT),
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"[!] NLI server error: {e}")
        return None