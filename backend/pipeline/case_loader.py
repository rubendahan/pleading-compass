"""Case loading and evidence preparation."""

from __future__ import annotations

import re
from pathlib import Path

from .schemas import CaseManifest, Evidence
from .simple_yaml import load_yaml


SUPPORTED_FORMATS = {"text", "markdown", "pdf"}


def load_case_manifest(case_dir: str | Path) -> CaseManifest:
    case_dir = Path(case_dir)
    data = load_yaml(case_dir / "manifest.yaml")
    manifest = CaseManifest.model_validate(data)
    validate_manifest_paths(case_dir, manifest)
    return manifest


def validate_manifest_paths(case_dir: Path, manifest: CaseManifest) -> None:
    missing: list[str] = []
    for rel_path in [manifest.pleading, manifest.bundle_index, *manifest.pleading_sources]:
        if rel_path and not (case_dir / rel_path).exists():
            missing.append(rel_path)
    for item in manifest.evidence:
        for rel_path in [item.path, item.source_path]:
            if rel_path and not (case_dir / rel_path).exists():
                missing.append(rel_path)
    if missing:
        raise FileNotFoundError(
            "Case manifest references missing file(s): " + ", ".join(sorted(missing))
        )


def load_pleading(case_dir: str | Path, manifest: CaseManifest) -> str:
    return (Path(case_dir) / manifest.pleading).read_text(encoding="utf-8")


def build_evidence_nodes(case_dir: str | Path, manifest: CaseManifest) -> list[Evidence]:
    case_dir = Path(case_dir)
    evidence_nodes: list[Evidence] = []
    for item in manifest.evidence:
        try:
            raw_text = _read_supported_text(case_dir / item.path, item.format)
            clean_text = clean_document_text(raw_text)
            evidence_nodes.append(
                Evidence(
                    id=item.id,
                    tab=item.tab,
                    path=item.path,
                    source_path=item.source_path,
                    type=item.type,
                    format=item.format,
                    source_format=item.source_format,
                    date=item.date,
                    period=item.period,
                    description=clean_text,
                    description_hint=item.description_hint,
                    raw_text=clean_text,
                    extraction_status="ok",
                )
            )
        except ValueError as exc:
            evidence_nodes.append(
                Evidence(
                    id=item.id,
                    tab=item.tab,
                    path=item.path,
                    source_path=item.source_path,
                    type=item.type,
                    format=item.format,
                    source_format=item.source_format,
                    date=item.date,
                    period=item.period,
                    description="",
                    description_hint=item.description_hint,
                    raw_text="",
                    extraction_status="unsupported",
                    extraction_error=str(exc),
                )
            )
        except Exception as exc:  # pragma: no cover - defensive file-system guard
            evidence_nodes.append(
                Evidence(
                    id=item.id,
                    tab=item.tab,
                    path=item.path,
                    source_path=item.source_path,
                    type=item.type,
                    format=item.format,
                    source_format=item.source_format,
                    date=item.date,
                    period=item.period,
                    description="",
                    description_hint=item.description_hint,
                    raw_text="",
                    extraction_status="failed",
                    extraction_error=str(exc),
                )
            )
    return evidence_nodes


def clean_document_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_supported_text(path: Path, evidence_format: str) -> str:
    if evidence_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported evidence format for phase 0: {evidence_format}")
    if evidence_format == "pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except ModuleNotFoundError as exc:
            raise ValueError("Install the `pdf` extra to extract PDF evidence.") from exc
        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")
