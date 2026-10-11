from typing import List

from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline


SBERT_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
NLI_MODEL_NAME = "facebook/bart-large-mnli"

app = FastAPI(
    title="Fact-Checking ML Service",
    version="1.0.0",
)


print(f"[*] Incarcare model SBERT ({SBERT_MODEL_NAME})...")
sbert_model = SentenceTransformer(SBERT_MODEL_NAME)

print(f"[*] Incarcare model NLI ({NLI_MODEL_NAME})...")
nli_pipeline = pipeline(
    "text-classification",
    model=NLI_MODEL_NAME,
)

print("[✓] Modelele SBERT si NLI sunt pregatite.")


class TextRequest(BaseModel):
    text: str


class BatchRequest(BaseModel):
    texts: List[str]


class SimilarityRequest(BaseModel):
    claim: str
    sentences: List[str]


class NLIRequest(BaseModel):
    premise: str
    hypothesis: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "sbert_model": SBERT_MODEL_NAME,
        "nli_model": NLI_MODEL_NAME,
    }


@app.post("/get_embedding")
def get_embedding(req: TextRequest):
    vector = sbert_model.encode(req.text).tolist()

    return {
        "embedding": vector,
    }


@app.post("/get_embeddings_batch")
def get_embeddings_batch(req: BatchRequest):
    vectors = sbert_model.encode(req.texts).tolist()

    return {
        "embeddings": vectors,
    }


@app.post("/get_similarity")
def get_similarity(req: SimilarityRequest):
    claim_vector = sbert_model.encode(req.claim)
    sentence_vectors = sbert_model.encode(req.sentences)

    scores = util.cos_sim(
        claim_vector,
        sentence_vectors,
    )[0].tolist()

    return {
        "scores": scores,
    }


@app.post("/check_nli")
def check_nli(req: NLIRequest):
    result = nli_pipeline(
        f"{req.premise} </s></s> {req.hypothesis}",
        top_k=None,
    )

    return {
        "scores": result,
    }