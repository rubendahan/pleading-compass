"""Similarity edge construction for phase 1."""

from __future__ import annotations

import math
from itertools import combinations

from .schemas import Claim, Edge, Evidence


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Cannot compare embeddings with different dimensions.")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def build_claim_evidence_similarity_edges(
    claims: list[Claim],
    evidence: list[Evidence],
) -> list[Edge]:
    edges: list[Edge] = []
    supported_evidence = [item for item in evidence if item.extraction_status == "ok"]
    for claim in claims:
        if claim.embedding is None:
            raise ValueError(f"Claim {claim.id} is missing an embedding.")
        for item in supported_evidence:
            if item.embedding is None:
                raise ValueError(f"Evidence {item.id} is missing an embedding.")
            edges.append(
                Edge(
                    source_id=claim.id,
                    target_id=item.id,
                    type="SIMILAR_TO",
                    score=cosine_similarity(claim.embedding, item.embedding),
                    rationale="Cosine similarity between claim text and evidence description embeddings.",
                    embedding_model_id=_shared_embedding_model_id(claim, item),
                )
            )
    return edges


def build_evidence_evidence_similarity_edges(evidence: list[Evidence]) -> list[Edge]:
    edges: list[Edge] = []
    supported_evidence = sorted(
        (item for item in evidence if item.extraction_status == "ok"),
        key=lambda item: item.id,
    )
    for source, target in combinations(supported_evidence, 2):
        if source.embedding is None:
            raise ValueError(f"Evidence {source.id} is missing an embedding.")
        if target.embedding is None:
            raise ValueError(f"Evidence {target.id} is missing an embedding.")
        edges.append(
            Edge(
                source_id=source.id,
                target_id=target.id,
                type="SIMILAR_TO",
                score=cosine_similarity(source.embedding, target.embedding),
                rationale="Cosine similarity between evidence description embeddings.",
                embedding_model_id=_shared_embedding_model_id(source, target),
            )
        )
    return edges


def _shared_embedding_model_id(left: Claim | Evidence, right: Claim | Evidence) -> str | None:
    if left.embedding_model_id and right.embedding_model_id:
        if left.embedding_model_id != right.embedding_model_id:
            raise ValueError(
                "Cannot compare embeddings from different models: "
                f"{left.embedding_model_id} and {right.embedding_model_id}."
            )
        return left.embedding_model_id
    return left.embedding_model_id or right.embedding_model_id
