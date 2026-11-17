"""Text embeddings with a local open model (no API key, no per-call cost).

intfloat/multilingual-e5-small: 384 dimensions, ~118M parameters, runs on CPU, and handles
German as well as English (useful for German inspection reports later).

E5 models are trained with prefixes: "query: " for search queries and "passage: " for the
documents being searched. Omitting them lowers retrieval quality, so they are added here,
in one place, instead of at every call site.

Embeddings are L2-normalised, so cosine distance in pgvector equals 1 - dot product.
"""

from functools import lru_cache
from typing import Protocol

from inspection_copilot.config import get_settings


class Embedder(Protocol):
    dim: int

    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class E5Embedder:
    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        # Imported lazily: torch takes seconds to import, and tests that use a fake
        # embedder should not pay for it.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device="cpu")
        self._batch_size = batch_size
        # Renamed in newer sentence-transformers; support both names.
        get_dim = (
            getattr(self._model, "get_embedding_dimension", None)
            or self._model.get_sentence_embedding_dimension
        )
        self.dim = get_dim()

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts, batch_size=self._batch_size, normalize_embeddings=True, show_progress_bar=False
        )
        return vectors.tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._encode([f"passage: {t}" for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._encode([f"query: {text}"])[0]


@lru_cache
def get_embedder() -> Embedder:
    """One model instance per process (loading it takes a few seconds and ~0.5 GB RAM)."""
    settings = get_settings()
    embedder = E5Embedder(settings.embedding_model)
    if embedder.dim != settings.embedding_dim:
        raise RuntimeError(
            f"model {settings.embedding_model} has dim {embedder.dim}, "
            f"but the database column expects {settings.embedding_dim}"
        )
    return embedder
