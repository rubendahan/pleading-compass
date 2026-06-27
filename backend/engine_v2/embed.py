"""Embedding adapter — real provider when configured, deterministic local fallback.

Ported from ``src/retrieval.py``. The real path calls Google Vertex AI
``text-embedding-004`` (drop-in when GCP creds are present); with no creds it
degrades to a deterministic, dependency-free hashed bag-of-tokens embedder so the
whole pipeline and its tests run fully offline and reproducibly.
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
    """Deterministic, offline embedding: hashed bag-of-tokens projected to ``dim``
    and unit-normalised. Reproducible and dependency-free — stands in until Vertex
    creds are present. Identical interface to the real embedder."""

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
    """A Vertex AI embedder if the SDK + creds are available, else ``None``."""
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


def openai_embedder(model: str = "text-embedding-3-small") -> Optional[Embedder]:
    """An OpenAI embedder if the SDK + ``OPENAI_API_KEY`` are available, else ``None``.

    Cached per-process so repeated paragraph embeddings within a run are free.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI
    except Exception:
        return None
    try:
        client = OpenAI()
    except Exception:
        return None
    model = os.getenv("EMBED_MODEL", model)

    class _OpenAI:
        def __init__(self):
            self._cache: dict[str, list[float]] = {}

        def embed(self, text: str) -> list[float]:
            key = text or " "
            if key in self._cache:
                return self._cache[key]
            try:
                vec = client.embeddings.create(model=model, input=key).data[0].embedding
                vec = [float(x) for x in vec]
            except Exception:
                vec = LocalEmbedder().embed(text)        # graceful per-call fallback
            self._cache[key] = vec
            return vec

    return _OpenAI()


def get_embedder(*, offline: bool = False) -> Embedder:
    """OpenAI if a key is present, else Vertex if configured, else the local
    deterministic fallback. ``offline`` (or ``ENGINE_FORCE_LOCAL_EMBED``) forces
    the instant local embedder — handy when you want LLM reasoning but fast,
    dependency-free retrieval."""
    if offline or os.getenv("ENGINE_FORCE_LOCAL_EMBED"):
        return LocalEmbedder()
    return openai_embedder() or vertex_embedder() or LocalEmbedder()


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def top_k(query_vec: list[float], items: list[tuple], k: int = 5) -> list[tuple]:
    """Rank ``items`` (each ``(key, vec)``) by cosine to ``query_vec``.

    Returns ``[(key, score), ...]`` descending; ties broken by ``str(key)`` for
    determinism.
    """
    scored = [(key, cosine(query_vec, vec)) for key, vec in items]
    scored.sort(key=lambda r: (-r[1], str(r[0])))
    return scored[:k]
