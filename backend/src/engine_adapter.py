"""The engine seam — one stable surface the trap harness drives, two backings.

A teammate is building ``engine_v2`` behind this exact contract::

    # engine_v2/api.py provides:
    #   @dataclass EngineVerdict(verdict: str, confidence: float, verify: bool,
    #                            evidence: list[tuple[str, int]], overlay: str, note: str = "")
    #   def assess_case(propositions, bundle, *, offline=True) -> dict[str, EngineVerdict]
    #        propositions: list of {id, text, pleaded_at:(tab, para)}
    #        bundle: {doc_id: {paras:[(n, text)], doc_type, party, date, category, modality}}
    #   def band(confidence: float) -> str   # "high">=0.66, "medium">=0.34, else "low"

This adapter wraps that API (``analyze_pleading``) with a *guarded* import, AND ships a
reference **gold-as-engine** oracle (``analyze_pleading_from_gold``) that turns an
engine-agnostic gold dict into the same ``EngineVerdict`` objects. The oracle lets the
trap harness be GREEN today — before the real engine lands — and lets the harness logic
itself be unit-tested without a model. Set ``EU_TRAPS_ENGINE=engine_v2`` to switch the
harness onto the real engine the moment it exists; otherwise the oracle is used.

``EngineVerdict`` is defined locally so the oracle needs no real engine; when the real
engine is present its own ``EngineVerdict`` is structurally identical (same attributes),
so both flow through the harness by duck typing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


__all__ = [
    "EngineVerdict",
    "band",
    "analyze_pleading",
    "analyze_pleading_from_gold",
    "assess",
    "engine_available",
    "selected_engine",
]


@dataclass
class EngineVerdict:
    """One per pleaded proposition — the shape ``engine_v2.api`` emits.

    ``verdict`` ∈ {SUPPORTED, CONTRADICTED, NOT_ADDRESSED, UNVERIFIED};
    ``overlay`` is the legal-risk overlay (NONE | CONTRACTUALLY_BARRED | SUPERSEDED |
    CAPPED | CAUSATION_PROBLEM | BURDEN_PROBLEM | TEMPORAL_SCOPE); ``evidence`` is the
    list of operative ``(doc, para)`` anchors; ``verify`` is True when a human must
    check (a VERIFY flag); ``confidence`` ∈ [0, 1]."""
    verdict: str
    confidence: float
    verify: bool
    evidence: list = field(default_factory=list)
    overlay: str = "NONE"
    note: str = ""


# Representative confidence per band, so ``band()`` round-trips the gold band exactly.
_BAND_CONFIDENCE = {"high": 0.9, "medium": 0.5, "low": 0.2}


@lru_cache(maxsize=1)
def _engine_module():
    """The real ``engine_v2.api`` module if importable, else ``None`` (guarded)."""
    try:
        import engine_v2.api as api  # type: ignore
        return api
    except Exception:
        return None


def engine_available() -> bool:
    """True iff the real ``engine_v2.api`` seam can be imported."""
    return _engine_module() is not None


def band(confidence: float) -> str:
    """Confidence band: ``high`` >= 0.66, ``medium`` >= 0.34, else ``low``.

    Re-exported from the real engine when present (so the harness uses the engine's
    own thresholds), with an identical local fallback for the gold-oracle path."""
    api = _engine_module()
    if api is not None and hasattr(api, "band"):
        try:
            return api.band(confidence)
        except Exception:
            pass
    if confidence >= 0.66:
        return "high"
    if confidence >= 0.34:
        return "medium"
    return "low"


def analyze_pleading(propositions, bundle) -> dict:
    """Drive the REAL engine: ``engine_v2.api.assess_case(propositions, bundle, offline=True)``.

    Raises ``RuntimeError`` if the engine is not importable — callers that want the
    automatic fallback should use :func:`assess` instead."""
    api = _engine_module()
    if api is None:
        raise RuntimeError(
            "engine_v2.api is not importable; use analyze_pleading_from_gold or assess().")
    return api.assess_case(propositions, bundle, offline=True)


def analyze_pleading_from_gold(gold: dict) -> dict:
    """Reference gold-as-engine oracle: project an engine-agnostic gold dict into
    ``{prop_id: EngineVerdict}``.

    Each gold entry supplies ``verdict``, ``confidence_band``, ``verify``,
    ``legal_risk`` (overlay), ``operative_evidence`` (the controlling anchors) and a
    ``rationale`` note. This makes the harness logic testable with no model and GREEN
    before the real engine exists."""
    out: dict = {}
    for pid, g in gold.items():
        out[pid] = EngineVerdict(
            verdict=g["verdict"],
            confidence=_BAND_CONFIDENCE.get(g.get("confidence_band", "low"), 0.2),
            verify=bool(g.get("verify", False)),
            evidence=[tuple(a) for a in g.get("operative_evidence", [])],
            overlay=g.get("legal_risk", "NONE"),
            note=g.get("rationale", ""),
        )
    return out


def selected_engine() -> str:
    """Which backing the harness uses: ``"engine_v2"`` if ``EU_TRAPS_ENGINE`` selects it
    AND the engine is importable, else ``"gold"`` (the reference oracle)."""
    if os.environ.get("EU_TRAPS_ENGINE") == "engine_v2" and engine_available():
        return "engine_v2"
    return "gold"


def assess(propositions, bundle, gold) -> dict:
    """Dispatch to the real engine when selected and available, else the gold oracle.

    The harness calls this: it is GREEN today via the oracle and switches to the real
    engine the moment ``EU_TRAPS_ENGINE=engine_v2`` is set and ``engine_v2.api`` exists.
    Returns ``{prop_id: EngineVerdict}`` either way."""
    if selected_engine() == "engine_v2":
        return analyze_pleading(propositions, bundle)
    return analyze_pleading_from_gold(gold)
