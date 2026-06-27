"""Phase 0b — build an `EvidenceNode` for every bundle paragraph.

Each node carries: a temporal parse (ISO-ish date if present), an ev_type drawn
from the document's metadata + light keyword cues (the source_type vocabulary), a
natural-language description (normalised text; a filename fallback stands in for
image/video evidence), a deterministic embedding, and a source-strength weight
(documents > experts > witnesses > pleadings).
"""
from __future__ import annotations

import re

from .embed import Embedder
from .models import Bundle, Document, EvidenceNode

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}

# doc_type -> (default source_type, weight)
_TYPE_WEIGHT = {
    "contract": ("signed_contract", 5.0),
    "pleading": ("pleading", 1.0),
    "expert": ("expert_report", 4.0),
    "witness": ("witness_statement", 2.0),
    "correspondence": ("contemporaneous_email", 4.0),
    "record": ("record", 4.0),
}


def parse_time(text: str, doc_date: str | None = None) -> str | None:
    """Best-effort date out of a paragraph; falls back to the document date."""
    t = text or ""
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        return m.group(0)
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", t)
    if m and m.group(2).lower() in _MONTHS:
        return f"{int(m.group(3)):04d}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return doc_date


def source_type_for(doc: Document, text: str) -> tuple[str, float]:
    base, weight = _TYPE_WEIGHT.get(doc.doc_type, ("record", 3.0))
    low = (doc.title + " " + text).lower()
    if "change order" in low or "deed of variation" in low:
        return "change_order", 5.0
    if "clause" in low and doc.doc_type == "contract":
        return "legal_clause", 5.0
    if "acceptance" in low or "uat" in low:
        return "acceptance_certificate", 5.0
    if "defect" in low:
        return "defect_log", 4.0
    return base, weight


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def build_evidence(bundle: Bundle, *, embedder: Embedder,
                   exclude_tab: str = "") -> list[EvidenceNode]:
    """One `EvidenceNode` per bundle paragraph (excluding the pleading tab)."""
    nodes: list[EvidenceNode] = []
    for doc in bundle.docs:
        if exclude_tab and doc.id == exclude_tab:
            continue
        for p in doc.paras:
            ev_type, strength = source_type_for(doc, p.text)
            if doc.modality in ("image", "photo", "video") and not p.text.strip():
                nl = doc.description or doc.file_url or doc.title or doc.id
            else:
                nl = _normalise(p.text)
            nodes.append(EvidenceNode(
                doc_id=doc.id, para=p.n, text=p.text,
                time=parse_time(p.text, doc.date), ev_type=ev_type,
                nl_description=nl, embedding=embedder.embed(nl or p.text),
                source_strength=strength,
            ))
    return nodes
