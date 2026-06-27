"""Real-bundle answer key — DRAFT, for the official CMS synthetic bundle.

Case: *Meridian Retail Group plc v TechFlow Solutions Ltd*, Claim HT-2025-000231
(Technology and Construction Court). The bundle pleads the **Claimant's** case only;
the Bundle Index states it is built so that "some pleaded allegations are well
supported by the evidence, some are contradicted by it, and some have little or no
supporting material." That construction is our ground-truth oracle.

Each proposition is an allegation in the Particulars of Claim (doc 02). Verdicts and
(doc_id, paragraph) anchors below were read off the parsed bundle and labelled from
the documents. **Draft — legal review pending** (Harvey's human-in-the-loop framing).

Anchors use the documents' own numbering where they number themselves (pleadings,
witness statements, expert reports) and sequential paragraph order otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models import Proposition  # noqa: E402

# All propositions are the Claimant's pleaded allegations (no Defence in the bundle).
def _p(pid: str, text: str) -> Proposition:
    return Proposition(pid, text, party="claimant", kind="allegation", burden="claimant")


PROPOSITIONS: list[Proposition] = [
    # Factual recitals of the Particulars of Claim (doc 02 ¶3-5). These are not
    # disputed allegations but the agreed contractual background, grounded in the
    # signed MSA/SOW. They are pleaded and therefore must be accounted for (SUPPORTED),
    # not left unannotated.
    _p("PR3", "By a written Master Services Agreement dated 14 March 2024 ('the MSA'), "
              "which the parties executed, TechFlow agreed to design, build, configure and "
              "implement for Meridian a cloud-based inventory management and EPOS platform "
              "('the Platform')."),
    _p("PR4", "The MSA incorporated a Statement of Work ('the SOW') at Schedule 1, which "
              "set out the scope of the works, the implementation plan and the milestones."),
    _p("PR5", "The total charges payable under the MSA were GBP 2,400,000 (excluding VAT), "
              "payable against milestones."),
    _p("P1", "TechFlow's Sales Director orally represented, before contract, that the "
             "Platform would reliably support at least 10,000 concurrent transactions, "
             "and the representation was false."),
    _p("P2", "TechFlow delivered the Platform late: it went live on 18 November 2024, "
             "seven weeks after the contractual go-live date of 1 October 2024, time being "
             "of the essence."),
    _p("P3", "Meridian did not request any change to the agreed scope; all delay was caused "
             "by TechFlow's failure to allocate adequate and competent resources."),
    _p("P4", "Meridian warned TechFlow the Platform was not ready and asked to defer go-live; "
             "TechFlow ignored those warnings and proceeded to go-live."),
    _p("P5", "Following go-live the Platform was unavailable for more than 40% of trading "
             "hours in November and December 2024, by reason of the Platform's own defects."),
    _p("P6", "The Platform contained numerous defects, including critical Severity-1 failures "
             "in the stock-synchronisation module, and was not of satisfactory quality nor fit "
             "for purpose."),
    _p("P7", "Meridian did not accept the Platform or any part of it, and gave no acceptance or "
             "sign-off at any time."),
    _p("P8", "TechFlow failed to provide adequate training to Meridian's staff in the use of "
             "the Platform."),
    _p("P9a", "Meridian suffered wasted expenditure of GBP 1,800,000, being sums paid to "
              "TechFlow under the MSA."),
    _p("P9b", "Meridian suffered loss of profit of GBP 4,200,000 during the November-December "
              "2024 peak trading period, caused by the Platform."),
]

# GOLD: verdict + (doc_id, para) evidence anchors. The stub rebuilds verbatim quotes
# from the bundle at these anchors, so they must point at the paragraph that carries
# the evidence. ``contradicts`` links to an opposing pleaded proposition (none here:
# the bundle pleads one side only — contradictions are pleaded-vs-evidence and emitted
# automatically for CONTRADICTED verdicts).
# Each entry also carries a second axis, ``legal_risk`` — an overlay distinguishing
# *evidential* outcome from *legal* defeat (a point can be NOT_ADDRESSED on the facts
# yet barred by a clause). Vocabulary: NONE | CONTRACTUALLY_BARRED | SUPERSEDED |
# CAPPED | CAUSATION_PROBLEM | BURDEN_PROBLEM.
GOLD: dict[str, dict] = {
    # --- Factual recitals: grounded in the signed contract documents (well supported) ---
    "PR3": {"verdict": "SUPPORTED",
            "evidence": [("03", 8), ("03", 24)], "contradicts": [],
            "legal_risk": "NONE",
            "note": "Grounded in the signed MSA: cl 1.1 (Tab 3 / doc 03 ¶8) records that the "
                    "Supplier shall design, build, configure, test and implement the Platform "
                    "per the SOW at Schedule 1; the agreement is executed by both parties (¶24)."},
    "PR4": {"verdict": "SUPPORTED",
            "evidence": [("03", 8), ("04", 4), ("04", 6), ("04", 11)], "contradicts": [],
            "legal_risk": "NONE",
            "note": "MSA cl 1.1 (Tab 3 ¶8) incorporates the SOW at Schedule 1; the SOW (Tab 4) "
                    "sets out the scope (cl 1.1 / ¶4), the implementation timetable (cl 2.1 / ¶6) "
                    "and the payment milestones (cl 4 / ¶11)."},
    "PR5": {"verdict": "SUPPORTED",
            "evidence": [("03", 11), ("04", 11)], "contradicts": [],
            "legal_risk": "NONE",
            "note": "MSA cl 2.1 (Tab 3 / doc 03 ¶11) fixes the total charges at GBP 2,400,000 "
                    "(excl VAT), payable against the milestones; the SOW cl 4 (Tab 4 ¶11) sets "
                    "the milestone payment schedule (25% on each of M1-M4)."},
    "P1": {"verdict": "NOT_ADDRESSED", "evidence": [], "contradicts": [],
           "legal_risk": "CONTRACTUALLY_BARRED",
           "note": "No document evidences the alleged pre-contract representation by Mr Frost "
                   "(10,000 concurrent transactions); MSA cl.22 (entire agreement / non-reliance) "
                   "would in any event bar reliance on it."},
    "P2": {"verdict": "CONTRADICTED",
           "evidence": [("07", 9), ("18", 3), ("16", 3)], "contradicts": [],
           "legal_risk": "SUPERSEDED",
           "note": "Go-live was contractually revised to 18 November 2024 by Change Order No. 3."},
    "P3": {"verdict": "CONTRADICTED",
           "evidence": [("07", 7), ("10", 4), ("18", 3)], "contradicts": [],
           "legal_risk": "NONE",
           "note": "Meridian itself requested the loyalty-module change (Change Order No. 3)."},
    "P4": {"verdict": "CONTRADICTED",
           "evidence": [("09", 5), ("16", 4), ("09", 10)], "contradicts": [],
           "legal_risk": "NONE",
           "note": "TechFlow recommended deferral in writing; Meridian's Programme Director "
                   "overruled it and instructed go-live, accepting the risk."},
    "P5": {"verdict": "CONTRADICTED",
           "evidence": [("19", 3), ("11", 4), ("17", 3), ("13", 3)], "contradicts": [],
           "legal_risk": "CAUSATION_PROBLEM",
           "note": "The IT expert puts Platform-attributable unavailability at ~6.2%, not 40%; "
                   "the largest outage was the Claimant's own network provider."},
    "P6": {"verdict": "SUPPORTED",
           "evidence": [("13", 5), ("13", 6), ("19", 5), ("19", 6), ("16", 5)], "contradicts": [],
           "legal_risk": "NONE",
           "note": "Genuine Severity-1 stock-sync defects, found below standard by the IT expert."},
    "P7": {"verdict": "CONTRADICTED",
           "evidence": [("08", 7), ("18", 4)], "contradicts": [],
           "legal_risk": "NONE",
           "note": "Meridian signed a Phase 1 UAT Acceptance Certificate on 12 November 2024."},
    "P8": {"verdict": "CONTRADICTED", "evidence": [("04", 9)], "contradicts": [],
           "legal_risk": "NONE",
           "note": "SOW cl 3.2 makes training of Meridian's own staff Meridian's responsibility; "
                   "TechFlow owed only a train-the-trainer session and written user guides. The "
                   "'failure to train' allegation is contradicted by the contract (Tab 4 / doc 04 "
                   "¶9)."},
    "P9a": {"verdict": "SUPPORTED",
            "evidence": [("20", 2), ("18", 5)], "contradicts": [],
            "legal_risk": "CAPPED",
            "note": "The quantum expert accepts the GBP 1.8m wasted expenditure (at/around the "
                    "MSA cl.14 liability cap)."},
    "P9b": {"verdict": "CONTRADICTED",
            "evidence": [("20", 4), ("20", 6), ("17", 4)], "contradicts": [],
            "legal_risk": "CAPPED",
            "note": "The quantum expert puts supportable loss of profit at ~GBP 1.3m, with much of "
                    "the Q4 shortfall attributable to a DC flood and the wider market; MSA cl.14 "
                    "excludes loss of profit and caps liability near GBP 1.8m."},
}

# Where each proposition is pleaded in the Particulars of Claim (doc 02).
PLEADED_AT: dict[str, tuple[str, int] | None] = {
    "PR3": ("02", 3), "PR4": ("02", 4), "PR5": ("02", 5),
    "P1": ("02", 7), "P2": ("02", 8), "P3": ("02", 9), "P4": ("02", 10),
    "P5": ("02", 11), "P6": ("02", 12), "P7": ("02", 13), "P8": ("02", 14),
    "P9a": ("02", 15), "P9b": ("02", 15),
}
