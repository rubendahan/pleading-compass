"""Self-test answer key — pleaded propositions + GOLD verdicts.

Anchored on *Bates v Post Office* [2019] EWHC 3408 (QB). This is a LABELLED
mini-bundle used to validate the harness/scorer offline (you can only trust a
scorer on data whose answers you know). The REAL answer key is built from the
official CMS bundle once it lands in ``data/bundle/``.

Paragraph anchors below refer to the numbered paragraphs in
``data/selftest/bundle/*.md``.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow ``import`` of the package model whether run via pytest (cwd on path) or
# directly. The proto root is two levels up from this file.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models import Proposition  # noqa: E402

PROPOSITIONS: list[Proposition] = [
    Proposition("P1", "Horizon contained bugs capable of generating apparent shortfalls "
                "that did not reflect any real loss.", "claimant", "allegation", "claimant"),
    Proposition("P2", "The Defendant could access and alter branch transaction data "
                "remotely, without the subpostmaster's knowledge.", "claimant", "allegation", "claimant"),
    Proposition("P3", "The Defendant's senior management knew, or ought to have known, "
                "of the defects in Horizon.", "claimant", "allegation", "claimant"),
    Proposition("D1", "Horizon was accurate and robust; shortfalls were caused by "
                "subpostmaster error or dishonesty.", "defendant", "defence", "defendant"),
    Proposition("D2", "The Defendant had no ability to alter branch transaction data "
                "remotely.", "defendant", "defence", "defendant"),
    Proposition("G1", "The subpostmaster received adequate training on the Horizon "
                "system.", "defendant", "defence", "defendant"),
]

# GOLD: verdict + the (doc_id, para) anchors that establish it + which other
# propositions it contradicts. ``single_source`` flags reliance on one document.
GOLD: dict[str, dict] = {
    "P1": {"verdict": "SUPPORTED",
           "evidence": [("05", 3), ("06", 2), ("03", 2)], "contradicts": []},
    "P2": {"verdict": "SUPPORTED",
           "evidence": [("04", 2)], "contradicts": ["D2"], "single_source": True},
    "P3": {"verdict": "NOT_ADDRESSED", "evidence": [], "contradicts": [],
           "note": "No document establishes senior-management knowledge; the internal "
                   "email (06) is operational, not evidence of what management knew."},
    "D1": {"verdict": "CONTRADICTED",
           "evidence": [("05", 3), ("06", 2), ("03", 3)], "contradicts": []},
    "D2": {"verdict": "CONTRADICTED",
           "evidence": [("04", 2)], "contradicts": ["P2"]},
    "G1": {"verdict": "NOT_ADDRESSED", "evidence": [], "contradicts": [],
           "note": "No document in the bundle addresses Horizon training."},
}

# Where each proposition is pleaded (doc_id, para) — anchors pleading↔proof
# contradictions. G1 is a constructed gap, pleaded nowhere in the bundle.
PLEADED_AT: dict[str, tuple[str, int] | None] = {
    "P1": ("01", 2), "P2": ("01", 3), "P3": ("01", 4),
    "D1": ("02", 2), "D2": ("02", 3), "G1": None,
}
