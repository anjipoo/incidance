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