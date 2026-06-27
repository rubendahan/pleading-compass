"""Phase 0 orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from .case_loader import build_evidence_nodes, load_case_manifest, load_pleading
from .config import AppConfig
from .embeddings import build_embedding_client, embed_with_chunk_centroid
from .graph_store import build_graph_document, ensure_output_dir, write_neo4j_graph
from .model_providers import build_llm_client
from .prompts import load_prompt
from .schemas import Claim, Evidence, RunMetadata


def run_phase0(
    *,
    case_dir: str | Path,
    config: AppConfig,
    config_path: str | Path,
    output_dir: str | Path,
    prompts_dir: str | Path = "prompts",
) -> RunMetadata:
    case_dir = Path(case_dir)
    output_dir = ensure_output_dir(output_dir)
    prompts_dir = Path(prompts_dir)
    warnings: list[str] = []

    manifest = load_case_manifest(case_dir)
    pleading_text = load_pleading(case_dir, manifest)
    prompt = load_prompt(prompts_dir / "claim_extraction.v1.md")

    trace_path = output_dir / "llm_calls.jsonl" if config.outputs.write_llm_traces else None
    llm_client = build_llm_client(config.llm)
    extraction_result = llm_client.extract_claims(
        prompt=prompt,
        pleading_text=pleading_text,
        trace_path=trace_path,
    )
    claims = [
        Claim(
            id=item.claim_id,
            text=item.text,
            source_quote=item.source_quote,
            paragraph_refs=item.paragraph_refs,
            cited_evidence_ids=item.cited_evidence_ids,
        )
        for item in extraction_result.claims
    ]

    evidence = build_evidence_nodes(case_dir, manifest)
    if any(item.extraction_status != "ok" for item in evidence):
        failed_ids = [item.id for item in evidence if item.extraction_status != "ok"]
        message = "Some evidence files were not extracted: " + ", ".join(failed_ids)
        if config.run.fail_on_unsupported_evidence:
            raise RuntimeError(message)
        warnings.append(message)

    embedding_client = build_embedding_client(config.embeddings)
    _embed_claims(claims, embedding_client, config.embeddings.max_chunk_chars)
    _embed_evidence(evidence, embedding_client, config.embeddings.max_chunk_chars)

    graph = build_graph_document(claims, evidence)
    write_neo4j_graph(graph, config.neo4j, warnings=warnings)

    metadata = RunMetadata(
        run_id=output_dir.name,
        timestamp=datetime.now(UTC).replace(microsecond=0).isoformat(),
        case_id=manifest.case_id,
        config_path=str(config_path),
        prompt_id=prompt.prompt_id,
        llm_provider=llm_client.provider_name,
        llm_model_id=llm_client.model_id,
        embedding_provider=embedding_client.provider_name,
        embedding_model_id=embedding_client.model_id,
        neo4j_enabled=config.neo4j.enabled,
        warnings=warnings,
    )

    _write_json(output_dir / "claims.json", [_dump_claim(item, config) for item in claims])
    _write_json(output_dir / "evidence.json", [_dump_evidence(item, config) for item in evidence])
    _write_json(output_dir / "graph.json", graph.model_dump())
    _write_json(output_dir / "run_metadata.json", metadata.model_dump())
    return metadata


def _embed_claims(claims, embedding_client, max_chunk_chars: int) -> None:
    for claim in claims:
        claim.embedding = embed_with_chunk_centroid(
            claim.text,
            embedding_client,
            max_chunk_chars=max_chunk_chars,
        )
        claim.embedding_model_id = embedding_client.model_id


def _embed_evidence(evidence: list[Evidence], embedding_client, max_chunk_chars: int) -> None:
    for item in evidence:
        if item.extraction_status != "ok":
            continue
        item.embedding = embed_with_chunk_centroid(
            item.description,
            embedding_client,
            max_chunk_chars=max_chunk_chars,
        )
        item.embedding_model_id = embedding_client.model_id


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
