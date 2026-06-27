"""Phase 1 edge computation."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from .config import AppConfig
from .graph_store import build_graph_document, ensure_output_dir, write_neo4j_graph
from .model_providers import build_llm_client
from .prompts import load_prompt
from .schemas import Claim, Edge, Evidence, EvidencePairReview, GraphDocument, Phase1RunMetadata
from .similarity import (
    build_claim_evidence_similarity_edges,
    build_evidence_evidence_similarity_edges,
)


def run_phase1(
    *,
    phase0_dir: str | Path,
    config: AppConfig,
    config_path: str | Path,
    output_dir: str | Path,
    prompts_dir: str | Path = "prompts",
) -> Phase1RunMetadata:
    phase0_dir = Path(phase0_dir)
    output_dir = ensure_output_dir(output_dir)
    prompts_dir = Path(prompts_dir)
    warnings: list[str] = []

    claims = _load_claims(phase0_dir / "claims.json")
    evidence = _load_evidence(phase0_dir / "evidence.json")
    phase0_metadata = _load_json_object(phase0_dir / "run_metadata.json")
    _validate_phase0_embeddings(claims, evidence)

    prompt = load_prompt(prompts_dir / "evidence_pair_review.v1.md")
    llm_client = build_llm_client(config.llm)
    trace_path = output_dir / "llm_calls.jsonl" if config.outputs.write_llm_traces else None
    if trace_path and trace_path.exists():
        trace_path.unlink()

    base_graph = build_graph_document(claims, evidence)
    claim_evidence_edges = build_claim_evidence_similarity_edges(claims, evidence)
    evidence_similarity_edges = build_evidence_evidence_similarity_edges(evidence)
    reviews, review_edges = _review_evidence_pairs(
        evidence=evidence,
        pair_edges=evidence_similarity_edges,
        prompt=prompt,
        llm_client=llm_client,
        trace_path=trace_path,
    )

    all_edges = _dedupe_edges(
        [
            *base_graph.edges,
            *claim_evidence_edges,
            *evidence_similarity_edges,
            *review_edges,
        ]
    )
    graph = GraphDocument(nodes=base_graph.nodes, edges=all_edges)
    write_neo4j_graph(graph, config.neo4j, warnings=warnings)

    metadata = Phase1RunMetadata(
        run_id=output_dir.name,
        timestamp=datetime.now(UTC).replace(microsecond=0).isoformat(),
        case_id=str(phase0_metadata.get("case_id", "")),
        source_phase0_dir=str(phase0_dir),
        config_path=str(config_path),
        prompt_id=prompt.prompt_id,
        llm_provider=llm_client.provider_name,
        llm_model_id=llm_client.model_id,
        embedding_provider=phase0_metadata.get("embedding_provider"),
        embedding_model_id=phase0_metadata.get("embedding_model_id"),
        neo4j_enabled=config.neo4j.enabled,
        claim_evidence_similarity_edges=len(claim_evidence_edges),
        evidence_evidence_similarity_edges=len(evidence_similarity_edges),
        support_edges=sum(1 for edge in review_edges if edge.type == "SUPPORTS"),
        contradict_edges=sum(1 for edge in review_edges if edge.type == "CONTRADICTS"),
        evidence_pair_reviews=len(reviews),
        warnings=warnings,
    )

    _write_json(output_dir / "claims.json", [_dump_claim(item, config) for item in claims])
    _write_json(output_dir / "evidence.json", [_dump_evidence(item, config) for item in evidence])
    _write_json(output_dir / "edges.json", [edge.model_dump() for edge in all_edges])
    _write_json(
        output_dir / "evidence_pair_reviews.json",
        [review.model_dump() for review in reviews],
    )
    _write_json(output_dir / "graph.json", graph.model_dump())
    _write_json(output_dir / "run_metadata.json", metadata.model_dump())
    return metadata


def _review_evidence_pairs(
    *,
    evidence: list[Evidence],
    pair_edges: list[Edge],
    prompt,
    llm_client,
    trace_path: Path | None,
) -> tuple[list[EvidencePairReview], list[Edge]]:
    evidence_by_id = {item.id: item for item in evidence}
    reviews: list[EvidencePairReview] = []
    review_edges: list[Edge] = []

    for pair_edge in pair_edges:
        source = evidence_by_id[pair_edge.source_id]
        target = evidence_by_id[pair_edge.target_id]
        review = llm_client.review_evidence_pair(
            prompt=prompt,
            source_evidence=_evidence_for_prompt(source),
            target_evidence=_evidence_for_prompt(target),
            trace_path=trace_path,
        )
        _validate_review_ids(review, pair_edge)
        reviews.append(review)
        _attach_review_metadata(
            pair_edge=pair_edge,
            review=review,
            prompt_id=prompt.prompt_id,
            model_id=llm_client.model_id,
        )

        if review.relation in {"supports", "contradicts"}:
            review_edges.append(
                Edge(
                    source_id=pair_edge.source_id,
                    target_id=pair_edge.target_id,
                    type=review.relation.upper(),
                    score=review.score,
                    rationale=review.rationale,
                    reasoning_summary=review.reasoning_summary,
                    confidence=review.confidence,
                    review_relation=review.relation,
                    review_score=review.score,
                    review_rationale=review.rationale,
                    prompt_id=prompt.prompt_id,
                    model_id=llm_client.model_id,
                    review_prompt_id=prompt.prompt_id,
                    review_model_id=llm_client.model_id,
                )
            )

    return reviews, review_edges


def _attach_review_metadata(
    *,
    pair_edge: Edge,
    review: EvidencePairReview,
    prompt_id: str,
    model_id: str,
) -> None:
    pair_edge.review_relation = review.relation
    pair_edge.review_score = review.score
    pair_edge.review_rationale = review.rationale
    pair_edge.reasoning_summary = review.reasoning_summary
    pair_edge.confidence = review.confidence
    pair_edge.review_prompt_id = prompt_id
    pair_edge.review_model_id = model_id


def _validate_phase0_embeddings(claims: list[Claim], evidence: list[Evidence]) -> None:
    for claim in claims:
        if not claim.embedding:
            raise RuntimeError(f"Claim {claim.id} is missing an embedding from phase 0.")
    for item in evidence:
        if item.extraction_status != "ok":
            continue
        if not item.embedding:
            raise RuntimeError(f"Evidence {item.id} is missing an embedding from phase 0.")


def _validate_review_ids(review: EvidencePairReview, pair_edge: Edge) -> None:
    if (
        review.source_evidence_id != pair_edge.source_id
        or review.target_evidence_id != pair_edge.target_id
    ):
        raise RuntimeError(
            "Evidence-pair review returned ids that do not match the requested pair: "
            f"expected {pair_edge.source_id}->{pair_edge.target_id}, "
            f"got {review.source_evidence_id}->{review.target_evidence_id}."
        )


def _evidence_for_prompt(evidence: Evidence) -> dict:
    return evidence.model_dump(exclude={"embedding", "raw_text"}, exclude_none=True)


def _dedupe_edges(edges: list[Edge]) -> list[Edge]:
    deduped: dict[tuple[str, str, str], Edge] = {}
    for edge in edges:
        deduped[(edge.source_id, edge.target_id, edge.type)] = edge
    return list(deduped.values())


def _load_claims(path: Path) -> list[Claim]:
    return [Claim.model_validate(item) for item in _load_json_array(path)]


def _load_evidence(path: Path) -> list[Evidence]:
    return [Evidence.model_validate(item) for item in _load_json_array(path)]


def _load_json_array(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"Expected JSON array in {path}.")
    return data


def _load_json_object(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected JSON object in {path}.")
    return data


def _dump_claim(claim: Claim, config: AppConfig) -> dict:
    exclude = set()
    if not config.outputs.include_embeddings_in_json:
        exclude.add("embedding")
    return claim.model_dump(exclude=exclude)


def _dump_evidence(evidence: Evidence, config: AppConfig) -> dict:
    exclude = set()
    if not config.outputs.include_embeddings_in_json:
        exclude.add("embedding")
    return evidence.model_dump(exclude=exclude)


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
