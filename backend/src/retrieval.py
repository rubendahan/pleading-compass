"""Semantic retrieval adapter — Google Vertex AI text-embeddings, with a local fallback.

The lexical RAG judge and the coverage report are blind to meaning: the decisive paragraph
is often not word-similar to the proposition. This adapter swaps token overlap for
embedding cosine. The real path calls **Vertex AI** ``text-embedding-004``; with no GCP
creds it degrades to a deterministic, dependency-free local embedder so everything stays
testable and offline. The interface is identical, so Vertex is a one-line drop-in.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Optional, Protocol

_TOKEN = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class LocalEmbedder:
    """Deterministic, offline embedding: hashed bag-of-tokens projected to ``dim`` and
    unit-normalised. Not semantic like Vertex — but reproducible and dependency-free, so
    the pipeline and its tests run anywhere. Stands in until Vertex creds are present."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in _TOKEN.findall((text or "").lower()):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            v[h % self.dim] += 1.0
            v[(h // self.dim) % self.dim] += 0.5          # second slot eases collisions
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]


def vertex_embedder(model: str = "text-embedding-004") -> Optional[Embedder]:
    """A Vertex AI embedder if the SDK + creds are available, else ``None``.

    Enable on a GCP box with Application Default Credentials and
    ``GOOGLE_CLOUD_PROJECT`` set (and ``pip install google-cloud-aiplatform``)."""
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        return None
    try:
        import vertexai
        from vertexai.language_models import TextEmbeddingModel
    except Exception:
        return None
    try:
        vertexai.init(project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                      location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
        m = TextEmbeddingModel.from_pretrained(model)
    except Exception:
        return None

    class _Vertex:
        def embed(self, text: str) -> list[float]:
            return list(m.get_embeddings([text])[0].values)

    return _Vertex()


def get_embedder() -> Embedder:
    """Vertex if configured, otherwise the deterministic local fallback."""
    return vertex_embedder() or LocalEmbedder()


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def semantic_rank(query: str, bundle, *, embedder: Optional[Embedder] = None,
                  k: int = 5) -> list[tuple[str, int, float]]:
    """Top-*k* paragraphs by embedding cosine to *query*, as ``(doc_id, para, score)``
    descending (ties broken by anchor for determinism)."""
    e = embedder or get_embedder()
    qv = e.embed(query)
    scored = [(doc_id, para, cosine(qv, e.embed(text)))
              for doc_id, para, text in bundle.iter_paras()]
    scored.sort(key=lambda r: (-r[2], r[0], r[1]))
    return scored[:k]
