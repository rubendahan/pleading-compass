"""The stable seam other code imports. Keep these signatures stable.

    assess_case(propositions, bundle, *, offline=True) -> dict[str, EngineVerdict]
    to_appdata(propositions, bundle, *, offline=True) -> dict
    band(confidence) -> "high" | "medium" | "low"

``propositions``: a list of ``{id, text, pleaded_at:(tab,para)}`` dicts OR a
pleading ``Document``.  ``bundle``: a dict ``{doc_id: {paras:[(n,text)], doc_type,
party, date, ...}}`` OR a ``Bundle``. Both forms are accepted.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import pipeline


@dataclass
class EngineVerdict:
    verdict: str                                  # SUPPORTED | CONTRADICTED | NOT_ADDRESSED | UNVERIFIED
    confidence: float                             # calibrated, [0, 1]
    verify: bool                                  # raise the human-verify flag
    evidence: list[tuple[str, int]] = field(default_factory=list)  # (tab, para) anchors
    overlay: str = "NONE"                         # legal-risk overlay
    note: str = ""


def band(confidence: float) -> str:
    """Confidence band: ``high`` ≥ 0.66, ``medium`` ≥ 0.34, else ``low``."""
    if confidence >= 0.66:
        return "high"
    if confidence >= 0.34:
        return "medium"
    return "low"


def assess_case(propositions, bundle, *, offline: bool = True) -> dict[str, "EngineVerdict"]:
    """Per pleaded proposition → an `EngineVerdict`.

    Includes synthesized propositions for any pleading paragraph that carried no
    allegation, so EVERY paragraph (incl. ``02¶6``) resolves to a verdict.
    """
    an = pipeline.analyze(propositions, bundle, offline=offline)
    out: dict[str, EngineVerdict] = {}
    for pid, a in an.assessments.items():
        note = "; ".join(a.reasons)
        if a.verdict == "NOT_ADDRESSED" and a.coverage:
            cov = a.coverage
            note = (f"{cov['paras_inspected']} ¶ inspected · best "
                    f"{cov['best_anchor'] or '—'} @ {cov['max_similarity']:.2f} "
                    f"< {cov['threshold']:.2f}" + (f"; {note}" if note else ""))
        out[pid] = EngineVerdict(
            verdict=a.verdict, confidence=a.confidence, verify=a.verify,
            evidence=list(a.evidence), overlay=a.legal_risk, note=note,
        )
    return out


def to_appdata(propositions, bundle, *, offline: bool = True) -> dict:
    """Full AppData JSON (BACKEND-OUTPUT-SPEC.md) the frontend consumes."""
    return pipeline.to_appdata(propositions, bundle, offline=offline)
