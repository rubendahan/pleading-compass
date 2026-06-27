"""Tests for the semantic-retrieval adapter (Google Vertex angle).

The real path calls Vertex AI text-embeddings; offline we exercise the deterministic local
fallback so the engine stays testable with no GCP creds. Vertex is a drop-in: same interface.
"""
from __future__ import annotations

from src import retrieval
from src.ingest import load_bundle

BUNDLE = "data/selftest/bundle"


def test_local_embedder_is_deterministic_and_unit_norm():
    e = retrieval.LocalEmbedder(dim=64)
    v1 = e.embed("change order revised go-live")
    v2 = e.embed("change order revised go-live")
    assert v1 == v2
    assert abs(retrieval.cosine(v1, v1) - 1.0) < 1e-9


def test_cosine_is_bounded():
    e = retrieval.LocalEmbedder(dim=128)
    a = e.embed("acceptance certificate signed")
    b = e.embed("loss of profit quantum cap")
    assert -1.0 <= retrieval.cosine(a, b) <= 1.0
    assert retrieval.cosine(a, a) > 0.999


def test_semantic_rank_finds_the_exact_paragraph():
    bundle = load_bundle(BUNDLE)
    e = retrieval.LocalEmbedder()
    did, n, text = next(bundle.iter_paras())
    rows = retrieval.semantic_rank(text, bundle, embedder=e, k=3)
    assert (rows[0][0], rows[0][1]) == (did, n)        # exact text is its own best match
    assert len(rows) == 3
    assert rows[0][2] >= rows[1][2] >= rows[2][2]      # descending score


def test_get_embedder_falls_back_to_local_without_vertex():
    e = retrieval.get_embedder()                       # no GCP creds -> LocalEmbedder
    assert e is not None
    assert len(e.embed("hello world")) > 0


def test_coverage_accepts_an_embedder_for_semantic_scoring():
    from src import coverage
    from src.pleadings import seed_propositions
    bundle = load_bundle(BUNDLE)
    p = seed_propositions()[0]
    rep = coverage.coverage_report(p, bundle, embedder=retrieval.LocalEmbedder())
    assert rep.paras_inspected == sum(1 for _ in bundle.iter_paras())
    assert 0.0 <= rep.max_similarity <= 1.0
    assert len(rep.queries) >= 1
