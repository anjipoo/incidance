import json
import numpy as np
from sentence_transformers import SentenceTransformer

# Lightweight, fast model — good tradeoff of quality vs. speed/size for a
# portfolio project. Loaded once at module import time so it's reused
# across requests instead of reloading per call.
MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    # Lazy singleton: avoids loading the model until it's actually needed
    # (useful for faster startup during early testing/imports).
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_text(text: str) -> np.ndarray:
    # Encodes a single string into a 384-dim embedding vector.
    model = get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding


def load_incident_dataset(path: str = "backend/data/incidents.json") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def embed_incident_dataset(incidents: list[dict]) -> np.ndarray:
    # Embeds every incident's "log" field in one batch call, which is
    # much faster than encoding one at a time.
    model = get_model()
    logs = [incident["log"] for incident in incidents]
    embeddings = model.encode(logs, convert_to_numpy=True, show_progress_bar=True)
    return embeddings

import faiss

# Global index + incident lookup, built once at startup and reused across requests.
_index: faiss.Index | None = None
_incidents: list[dict] | None = None


def _normalize(vectors: np.ndarray) -> np.ndarray:
    # FAISS's IndexFlatIP computes inner product, not cosine similarity
    # directly. But inner product on L2-normalized vectors IS mathematically
    # equivalent to cosine similarity. So we normalize every vector to unit
    # length here, then use inner product search to get cosine results.
    faiss.normalize_L2(vectors)
    return vectors


def build_index(incidents: list[dict] | None = None) -> None:
    # Builds the FAISS index from the seed dataset. Call once at app startup.
    global _index, _incidents

    if incidents is None:
        incidents = load_incident_dataset()

    embeddings = embed_incident_dataset(incidents)
    embeddings = embeddings.astype("float32")  # FAISS requires float32
    _normalize(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # IP = inner product
    index.add(embeddings)

    _index = index
    _incidents = incidents


def search_similar(query_text: str, top_k: int = 3) -> list[dict]:
    # Embeds the query, searches the index, and returns the top_k most
    # similar historical incidents with their similarity scores.
    if _index is None or _incidents is None:
        raise RuntimeError("FAISS index not built yet — call build_index() first")

    query_vec = embed_text(query_text).astype("float32").reshape(1, -1)
    _normalize(query_vec)

    similarities, indices = _index.search(query_vec, top_k)

    results = []
    for score, idx in zip(similarities[0], indices[0]):
        if idx == -1:  # FAISS returns -1 if fewer than top_k results exist
            continue
        incident = _incidents[idx]
        results.append({
            "id": incident["id"],
            "log": incident["log"],
            "category": incident["category"],
            "severity": incident["severity"],
            "root_cause": incident["root_cause"],
            "resolution": incident["resolution"],
            "similarity": float(score),
        })
    return results