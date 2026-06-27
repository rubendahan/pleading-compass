"""Chronology of Facts — counsel-prepared, deterministic fixture.

Seeded verbatim from the instructing lawyer's "Legal Analysis of Pleadings" (the
Chronology of Facts they prepared by hand). Each fact carries its evidence anchors
(tab/paragraph) so the frontend's "verify" opens the real source. ``source="counsel"``
marks every row as human-verified — NOT an LLM inference. For a real, unseen bundle the
same array would instead be LLM-drafted with ``source="ai"`` and surfaced as "verify".

Tab numbers are the bundle document ids (doc id == Tab). Paragraph numbers use the
engine's numbering where known, else ``None`` (the reader degrades gracefully).
"""
from __future__ import annotations

CHRONOLOGY: list[dict] = [
    {"n": 1, "date": "2024-03-14",
     "event": "Meridian and TechFlow entered into the Master Services Agreement (MSA) to "
              "design, build and implement a cloud inventory-management and EPOS platform.",
     "evidence": [{"tab": "03", "para": None}, {"tab": "18", "para": 2}],
     "remarks": "", "source": "counsel"},
    {"n": 2, "date": "2024-03-14",
     "event": "The SOW (Schedule 1) set the scope, implementation plan and milestones; the "
              "1 October 2024 go-live was stated to be a target date.",
     "evidence": [{"tab": "04", "para": 6}], "remarks": "", "source": "counsel"},
    {"n": 3, "date": "2024-03-20",
     "event": "Meridian issued an Order Form (Phase 1); the charges payable under the MSA were "
              "GBP 2,400,000 (excluding VAT).",
     "evidence": [{"tab": "05", "para": None}], "remarks": "", "source": "counsel"},
    {"n": 4, "date": "2024-06-28",
     "event": "Deed of Variation No. 1 varied the payment-milestone profile in the SOW to "
              "reflect cash-flow phasing.",
     "evidence": [{"tab": "06", "para": None}], "remarks": "", "source": "counsel"},
    {"n": 5, "date": "2024-08-21",
     "event": "Helena Vance (Meridian) requested a Loyalty Module and was willing to revise the "
              "go-live date; on 27 August TechFlow quoted GBP 180,000 and a move to 18 Nov 2024.",
     "evidence": [{"tab": "10", "para": None}, {"tab": "16", "para": 3}],
     "remarks": "", "source": "counsel"},
    {"n": 6, "date": "2024-09-02",
     "event": "Change Order No. 3 was signed: it added the Loyalty Module (+GBP 180,000) and "
              "revised the go-live date from 1 October to 18 November 2024.",
     "evidence": [{"tab": "07", "para": 9}, {"tab": "18", "para": 3}],
     "remarks": "Supersedes the original 1 October go-live date.", "source": "counsel"},
    {"n": 7, "date": "2024-10-24",
     "event": "TechFlow recommended deferring go-live to mid-January 2025; Meridian elected to "
              "accept the risk and instructed go-live on 18 November 2024.",
     "evidence": [{"tab": "09", "para": 5}, {"tab": "08", "para": 7}, {"tab": "18", "para": 4}],
     "remarks": "", "source": "counsel"},
    {"n": 8, "date": "2024-11-26",
     "event": "TechFlow informed Meridian that the 25 November 2024 outage was caused by loss of "
              "wide-area network connectivity at Meridian's data-centre provider (Northgate).",
     "evidence": [{"tab": "11", "para": None}, {"tab": "13", "para": None}, {"tab": "17", "para": 3}],
     "remarks": "Okafor relays the cause as hearsay ('I am told').", "source": "counsel"},
    {"n": 9, "date": "2024-12-08",
     "event": "Okafor's internal email: December trading below plan; a DC flood closed the "
              "Lutterworth distribution centre for 10 days and the market was soft.",
     "evidence": [{"tab": "12", "para": None}, {"tab": "17", "para": 4}],
     "remarks": "Alternative causation for the Q4 shortfall.", "source": "counsel"},
    {"n": 10, "date": "2025-01-20",
     "event": "Meridian's solicitors issued a Notice of Termination of the MSA: late delivery, "
              "repeated failures, and not fit for purpose.",
     "evidence": [{"tab": "14", "para": None}], "remarks": "", "source": "counsel"},
    {"n": 11, "date": "2025-02-07",
     "event": "TechFlow's solicitors replied, disputing the grounds of termination.",
     "evidence": [{"tab": "15", "para": None}], "remarks": "", "source": "counsel"},
    {"n": 12, "date": "2025-06-05",
     "event": "Meridian filed its Claim at the High Court.",
     "evidence": [{"tab": "01", "para": None}, {"tab": "02", "para": None}],
     "remarks": "", "source": "counsel"},
]
