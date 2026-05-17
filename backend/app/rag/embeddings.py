"""sentence-transformers embeddings for ChromaDB."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_model = None
MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(MODEL_NAME)
            logger.info(f"Loaded sentence-transformer: {MODEL_NAME}")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformer: {e}")
    return _model


def embed_text(text: str) -> list[float]:
    model = _get_model()
    if model is None:
        # Return zero vector as fallback (384-dim for MiniLM)
        return [0.0] * 384
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    if model is None:
        return [[0.0] * 384 for _ in texts]
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [e.tolist() for e in embeddings]
