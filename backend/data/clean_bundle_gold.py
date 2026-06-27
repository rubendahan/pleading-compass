"""A tiny ALL-SUPPORTED control bundle — the cry-wolf / false-positive guard.

The trap harness (``tests/test_eu_traps.py``) proves the engine catches every planted
trap. That is only half of trustworthiness: an engine that flags *everything* is as
useless as one that flags nothing. This control is the positive case — four crisp,
unambiguous allegations, each restated verbatim by an authoritative document already in
the Brightmarket bundle. The correct verdict for every one is SUPPORTED · NONE · high ·
verify=False. If the engine raises a CONTRADICTED / NOT_ADDRESSED / UNVERIFIED here, or
flags a non-NONE overlay, it is crying wolf on a clean case.

Each supporting paragraph is reused VERBATIM from ``data/eu_case_gold._PARAS`` so the
quote is, by construction, a substring of its source paragraph.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data import eu_case_gold as EUG  # noqa: E402


def _src(doc: str, para: int) -> str:
    """Verbatim text of an existing eu_case paragraph (raises if missing — so a
    typo in an anchor fails loudly at import rather than silently de-grounding)."""
    for n, text in EUG._PARAS.get(doc, []):
        if n == para:
            return text
    raise KeyError(f"clean control references a missing paragraph {doc}¶{para}")


# Four crisp allegations, each pleaded at the clean Particulars of Claim ¶1..¶4.
CLEAN_PROPOSITIONS: list[dict] = [
    {"id": "CP1", "pleaded_at": ("02", 1),
     "text": "The annual subscription fee under the Order Form was EUR 900,000."},
    {"id": "CP2", "pleaded_at": ("02", 2),
     "text": "The Master Subscription Agreement is governed by the laws of Ireland."},
    {"id": "CP3", "pleaded_at": ("02", 3),
     "text": "Cobalt was appointed as the processor of Brightmarket's customer personal data."},
    {"id": "CP4", "pleaded_at": ("02", 4),
     "text": "Backups were taken as hourly snapshots of the production data stores."},
]

# Verbatim pleaded paragraphs for the clean Particulars of Claim (doc "02").
_CLEAN_PLEADED: dict[int, str] = {
    1: "The annual subscription fee under the Order Form was EUR 900,000.",
    2: "The Master Subscription Agreement is governed by the laws of Ireland.",
    3: "Cobalt was appointed as the processor of Brightmarket's customer personal data.",
    4: "Backups were taken as hourly snapshots of the production data stores.",
}

# Each clean allegation -> the authoritative document paragraph that supports it.
_SUPPORT: dict[str, tuple[str, int]] = {
    "CP1": ("06", 2),   # Order Form: annual subscription fee EUR 900,000
    "CP2": ("03", 1),   # MSA governed by the laws of Ireland
    "CP3": ("04", 1),   # DPA appoints the Supplier as processor
    "CP4": ("31", 2),   # DR runbook: hourly snapshots
}


CLEAN_GOLD: dict[str, dict] = {
    pid: {
        "trap_type": None,
        "issue": "CLEAN/CONTROL",
        "verdict": "SUPPORTED",
        "legal_risk": "NONE",
        "confidence_band": "high",
        "verify": False,
        "must_not": ["CONTRADICTED", "NOT_ADDRESSED", "UNVERIFIED"],
        "operative_evidence": [_SUPPORT[pid]],
        "decoy_evidence": [],
        "acts": [],
        "own_goal": False,
        "rationale": "Crisp, unambiguous allegation restated verbatim by an authoritative "
                     "document in the bundle — SUPPORTED with no legal overlay and no need "
                     "for human verification.",
    }
    for pid in ("CP1", "CP2", "CP3", "CP4")
}


def compose() -> tuple[list[dict], dict]:
    """Return ``(propositions, bundle)`` in the engine-seam shape for the clean control."""
    propositions = [dict(p) for p in CLEAN_PROPOSITIONS]

    used_docs = {doc for doc, _ in _SUPPORT.values()}
    bundle: dict = {
        "02": {
            "title": "Particulars of Claim (clean control)",
            "paras": [(n, t) for n, t in sorted(_CLEAN_PLEADED.items())],
            "doc_type": "pleading", "party": "claimant", "date": "2026-02-10",
            "category": "Pleading", "modality": "text",
        }
    }
    for doc in sorted(used_docs):
        title, doc_type, party, date, category, modality = EUG.DOC_META[doc]
        # Only the paragraphs actually relied on, copied verbatim from the source.
        paras = [(para, _src(doc, para)) for d, para in _SUPPORT.values() if d == doc]
        bundle[doc] = {"title": title, "paras": paras, "doc_type": doc_type,
                       "party": party, "date": date, "category": category,
                       "modality": modality}
    return propositions, bundle


def quote_for(pid: str) -> str:
    """The verbatim supporting quote for a clean allegation (the whole source paragraph)."""
    doc, para = _SUPPORT[pid]
    return _src(doc, para)
