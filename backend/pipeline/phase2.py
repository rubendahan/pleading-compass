"""Phase 2 claim robustness review."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from .config import AppConfig
from .graph_store import ensure_output_dir
from .model_providers import build_llm_client
from .prompts import load_prompt
from .schemas import (
    Claim,
    ClaimRobustnessReview,
    Edge,
    Evidence,
    Phase2RunMetadata,
)


def run_phase2(
    *,
    phase1_dir: str | Path,
    config: AppConfig,
    config_path: str | Path,
    output_dir: str | Path,
    prompts_dir: str | Path = "prompts",
    llm_client=None,
) -> Phase2RunMetadata:
    phase1_dir = Path(phase1_dir)
    output_dir = ensure_output_dir(output_dir)
    prompts_dir = Path(prompts_dir)
    warnings: list[str] = []

    claims_data = _load_json_array(phase1_dir / "claims.json")
    evidence_data = _load_json_array(phase1_dir / "evidence.json")
    edges_data = _load_json_array(phase1_dir / "edges.json")
    phase1_metadata = _load_json_object(phase1_dir / "run_metadata.json")

    claims = [Claim.model_validate(item) for item in claims_data]
    evidence = [Evidence.model_validate(item) for item in evidence_data]
    edges = [Edge.model_validate(item) for item in edges_data]
    evidence_by_id = {item.id: item for item in evidence}

    prompt = load_prompt(prompts_dir / "claim_robustness_review.v1.md")
    llm_client = llm_client or build_llm_client(config.llm)
    trace_path = output_dir / "llm_calls.jsonl" if config.outputs.write_llm_traces else None
    if trace_path and trace_path.exists():
        trace_path.unlink()

    reports: list[ClaimRobustnessReview] = []
    for claim in claims:
        selected_evidence = select_claim_evidence_context(
            claim=claim,
            evidence_by_id=evidence_by_id,
            edges=edges,
            top_k=config.phase2.claim_evidence_top_k,
        )
        evidence_relationships = collect_evidence_relationship_context(
            selected_evidence_ids=[item["evidence_id"] for item in selected_evidence],
            evidence_by_id=evidence_by_id,
            edges=edges,
        )
        report = llm_client.review_claim_robustness(
            prompt=prompt,
            claim=claim.model_dump(exclude={"embedding"}),
            selected_evidence=selected_evidence,
            evidence_relationships=evidence_relationships,
            trace_path=trace_path,
        )
        _validate_claim_report(report, claim)
        reports.append(report)

    metadata = Phase2RunMetadata(
        run_id=output_dir.name,
        timestamp=datetime.now(UTC).replace(microsecond=0).isoformat(),
        case_id=str(phase1_metadata.get("case_id", "")),
        source_phase1_dir=str(phase1_dir),
        config_path=str(config_path),
        prompt_id=prompt.prompt_id,
        llm_provider=llm_client.provider_name,
        llm_model_id=llm_client.model_id,
        claim_evidence_top_k=config.phase2.claim_evidence_top_k,
        claim_reports=len(reports),
        warnings=warnings,
    )

    _write_json(output_dir / "claim_reports.json", [item.model_dump() for item in reports])
    (output_dir / "claim_reports.md").write_text(
        render_claim_reports_markdown(reports),
        encoding="utf-8",
    )
    _copy_phase1_artifact(phase1_dir, output_dir, "claims.json")
    _copy_phase1_artifact(phase1_dir, output_dir, "evidence.json")
    _copy_phase1_artifact(phase1_dir, output_dir, "edges.json")
    _copy_phase1_artifact(phase1_dir, output_dir, "graph.json")
    _write_json(output_dir / "run_metadata.json", metadata.model_dump())
    return metadata


def select_claim_evidence_context(
    *,
    claim: Claim,
    evidence_by_id: dict[str, Evidence],
    edges: list[Edge],
    top_k: int,
) -> list[dict[str, Any]]:
    similarity_edges = [
        edge
        for edge in edges
        if edge.type == "SIMILAR_TO"
        and edge.source_id == claim.id
        and edge.target_id in evidence_by_id
    ]
    similarity_by_evidence = {edge.target_id: edge for edge in similarity_edges}

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    usage_edges = [
        edge
        for edge in edges
        if edge.type == "USES_EVIDENCE"
        and edge.source_id == claim.id
        and edge.target_id in evidence_by_id
    ]
    for edge in sorted(usage_edges, key=lambda item: item.target_id):
        selected.append(
            _selected_evidence_record(
                evidence=evidence_by_id[edge.target_id],
                selection_reason="USES_EVIDENCE",
                similarity_edge=similarity_by_evidence.get(edge.target_id),
                usage_edge=edge,
            )
        )
        selected_ids.add(edge.target_id)

    ranked_similarity_edges = sorted(
        similarity_edges,
        key=lambda item: (item.score if item.score is not None else -1.0, item.target_id),
        reverse=True,
    )
    added = 0
    for edge in ranked_similarity_edges:
        if edge.target_id in selected_ids:
            continue
        selected.append(
            _selected_evidence_record(
                evidence=evidence_by_id[edge.target_id],
                selection_reason="top_k_similarity",
                similarity_edge=edge,
                usage_edge=None,
            )
        )
        selected_ids.add(edge.target_id)
        added += 1
        if added >= top_k:
            break

    return selected


def collect_evidence_relationship_context(
    *,
    selected_evidence_ids: list[str],
    evidence_by_id: dict[str, Evidence],
    edges: list[Edge],
) -> dict[str, list[dict[str, Any]]]:
    selected_ids = set(selected_evidence_ids)
    context: dict[str, list[dict[str, Any]]] = {evidence_id: [] for evidence_id in selected_evidence_ids}

    for edge in edges:
        if edge.type not in {"SUPPORTS", "CONTRADICTS"}:
            continue
        involved_ids = [item for item in [edge.source_id, edge.target_id] if item in selected_ids]
        if not involved_ids:
            continue
        for evidence_id in involved_ids:
            other_id = edge.target_id if edge.source_id == evidence_id else edge.source_id
            other = evidence_by_id.get(other_id)
            context[evidence_id].append(
                {
                    "relation": edge.type,
                    "source_evidence_id": edge.source_id,
                    "target_evidence_id": edge.target_id,
                    "other_evidence_id": other_id,
                    "other_evidence_type": other.type if other else None,
                    "other_evidence_date": other.date if other else None,
                    "score": edge.score,
                    "rationale": edge.rationale,
                    "reasoning_summary": edge.reasoning_summary,
                    "confidence": edge.confidence.model_dump() if edge.confidence else None,
                    "prompt_id": edge.prompt_id or edge.review_prompt_id,
                    "model_id": edge.model_id or edge.review_model_id,
                }
            )

    for items in context.values():
        items.sort(
            key=lambda item: (item["relation"], item["score"] if item["score"] is not None else -1.0),
            reverse=True,
        )
    return context


def render_claim_reports_markdown(reports: list[ClaimRobustnessReview]) -> str:
    lines = ["# Claim Robustness Reports", ""]
    for report in reports:
        lines.extend(
            [
                f"## {report.claim_id}: {report.verdict.title()} ({report.robustness_score}/100)",
                "",
                f"**Claim:** {report.claim_text}",
                "",
                *(
                    [
                        f"**Verdict confidence:** {report.verdict_confidence:.2f}",
                        "",
                    ]
                    if report.verdict_confidence is not None
                    else []
                ),
                "### Supporting Evidence",
                *_render_findings(report.supporting_evidence),
                "",
                "### Challenging Evidence",
                *_render_findings(report.challenging_evidence),
                "",
                "### Missing Evidence",
                *_render_strings(report.missing_evidence),
                "",
                "### Over-Extrapolation Risks",
                *_render_strings(report.over_extrapolation_risks),
                "",
                "### Legal Explanation",
                "",
                report.legal_explanation,
                "",
                "### Recommended Action",
                "",
                report.recommended_action,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _selected_evidence_record(
    *,
    evidence: Evidence,
    selection_reason: str,
    similarity_edge: Edge | None,
    usage_edge: Edge | None,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence.id,
        "selection_reason": selection_reason,
        "claim_similarity_score": similarity_edge.score if similarity_edge else None,
        "claim_similarity_rationale": similarity_edge.rationale if similarity_edge else None,
        "uses_evidence_rationale": usage_edge.rationale if usage_edge else None,
        "metadata": {
            "id": evidence.id,
            "tab": evidence.tab,
            "path": evidence.path,
            "source_path": evidence.source_path,
            "type": evidence.type,
            "format": evidence.format,
            "date": evidence.date,
            "period": evidence.period,
        },
        "description": evidence.description,
    }


def _validate_claim_report(report: ClaimRobustnessReview, claim: Claim) -> None:
    if report.claim_id != claim.id:
        raise RuntimeError(
            "Claim robustness review returned the wrong claim id: "
            f"expected {claim.id}, got {report.claim_id}."
        )
    if report.claim_text != claim.text:
        raise RuntimeError(
            "Claim robustness review returned a claim_text that does not match "
            f"claim {claim.id}."
        )


def _render_findings(findings) -> list[str]:
    if not findings:
        return ["- None identified."]
    return [
        f"- `{item.evidence_id}`"
        + (f" ({item.score:.2f})" if item.score is not None else "")
        + f": {item.summary}"
        for item in findings
    ]


def _render_strings(items: list[str]) -> list[str]:
    if not items:
        return ["- None identified."]
    return [f"- {item}" for item in items]


def _copy_phase1_artifact(source_dir: Path, output_dir: Path, filename: str) -> None:
    source = source_dir / filename
    if source.exists():
        (output_dir / filename).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


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


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
