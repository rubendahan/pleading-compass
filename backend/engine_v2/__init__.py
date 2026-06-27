"""engine_v2 — a simple, general, tool-using pleading→proof analysis engine.

Given any pleading + bundle, returns per pleaded paragraph a verdict
(SUPPORTED / CONTRADICTED / NOT_ADDRESSED / UNVERIFIED) with a verbatim
source-anchored quote, a calibrated confidence and a VERIFY flag — and emits the
exact AppData JSON the frontend consumes. Runs fully offline (deterministic, no
key) via a stub, and uses Claude when ANTHROPIC_API_KEY is present.

Public seam (keep stable): ``api.assess_case``, ``api.to_appdata``, ``api.band``,
``api.EngineVerdict``.
"""
from __future__ import annotations

from .api import EngineVerdict, assess_case, band, to_appdata
from .models import (VERDICTS, OVERLAYS, RELATIONS, Assessment, Bundle, ClaimNode,
                     Document, Edge, EvidenceNode, Graph, Para)

__all__ = [
    "assess_case", "to_appdata", "band", "EngineVerdict",
    "VERDICTS", "OVERLAYS", "RELATIONS",
    "Bundle", "Document", "Para", "ClaimNode", "EvidenceNode", "Edge", "Graph",
    "Assessment",
]
