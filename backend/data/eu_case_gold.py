"""Second litigation test case — a much HARDER, MURKIER dispute grounded in REAL EU
legislation, in the same gold format as ``data/bundle_gold.py`` (Meridian).

Case: *Brightmarket Retail GmbH v Cobalt Cloud Analytics Ltd*, Commercial Court
(contract governed by Irish law; the parties are EU undertakings, so the EU data /
platform acquis applies). Brightmarket (a multi-country online retailer and **data
controller**) engaged Cobalt — a B2B SaaS analytics platform and **GDPR Article 28
processor** — under a Master Subscription Agreement (MSA), a Data Processing Agreement
(DPA), a Statement of Work (SOW) and later addenda. After a personal-data breach in
October 2025 Brightmarket sues. As with Meridian, the bundle pleads the **Claimant's**
case only and is constructed so that some pleaded allegations are well supported, some
are contradicted by the evidence, and **many are genuinely unclear** — "it depends /
needs more" rather than clean-cut.

This expansion deliberately makes the case *murky*. Ambiguity features:
  (a) DUELLING EXPERTS WHO PARTLY AGREE. Two forensic experts (Dr Vale, jointly
      instructed, doc 19; Prof Strand, Claimant-instructed, doc 21) AGREE that only
      ~14,000 records were actually exfiltrated, but DIVERGE on whether a far larger
      set (~1.9m) was "exposed" within GDPR Art 4(12), and on whether Cobalt's network
      segmentation was a *concurrent* Art 32 failing. Two quantum experts (Caron, doc
      20; Roos, doc 22) BOTH reject the EUR 6m figure but support different numbers
      (~EUR 1.1m vs ~EUR 0.4m) and split on how much fee was "wasted".
  (b) MULTI-LINK / CONCURRENT CAUSATION. The breach chain runs: disabled MFA (the
      Claimant's own admins) -> credential compromise -> lateral movement -> exfiltration.
      Vale puts the proximate cause on the disabled MFA; Strand says Cobalt's flat
      network was *also* a substantial contributing cause. "Caused SOLELY by Cobalt"
      (P5) therefore fails, but apportioned liability is live — a genuinely murky point.
  (c) PARTIAL SUPERSESSIONS. P8 rests on Directive 95/46/EC (CELEX 31995L0046), which
      the GDPR (Reg (EU) 2016/679, Art 94 — CELEX 32016R0679) repealed from 25 May 2018.
      Separately, the transfer *mechanism* (P8b) turns on which SCCs applied: the old
      2010/87/EU clauses (CELEX 32010D0087) were replaced by Commission Implementing
      Decision (EU) 2021/914 (CELEX 32021D0914), with a transition to 27 Dec 2022.
  (d) OWN-GOALS (the Claimant's own documents cut against it, in non-obvious ways).
      P5: Brightmarket's own internal security review admits its admins disabled MFA
      (doc 12). P3: Brightmarket's OWN breach notification to the DPC put the affected
      population at ~19,000 (doc 24) — flatly inconsistent with its pleaded 2.3m. P4:
      that same filing shows the *controller* notified the regulator (late), so the
      72h duty was Brightmarket's. P1: Brightmarket's own procurement due-diligence note
      records that it verified and relied on Cobalt's ISO 27001 certificate (doc 34).
  (e) HEARSAY. P6 rests on a witness relaying "I am told by our IT team…" (doc 16 ¶6);
      P12 and P13 likewise rest partly on second-hand witness belief (doc 18 ¶4/¶5).
  (f) ALLOCATION TRAP. P4 looks like an evidence gap ("Cobalt never notified the
      regulator") but under GDPR Art 33(1) and DPA cl 9.2 it is the **controller**
      (Brightmarket) that must notify the supervisory authority within 72h; the
      processor's duty (Art 33(2)) is only to notify the controller, which Cobalt did
      within 18h (doc 08).
  (g) THIN / INDIRECT / NOT-ADDRESSED points. The exposure-definition (P3b), the
      transfer-mechanism (P8b), the partial-restore (P9b), the cookie/ePrivacy (P13),
      the automated-decision/AI-Act (P12) and the DSAR/erasure (P14) allegations all
      rest on incomplete, ambiguous or absent evidence and resolve to UNVERIFIED or
      NOT_ADDRESSED — survives the coherence solver, but unproven on the facts.

Anchors use each document's own numbering. **Draft — legal review pending.**
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models import Bundle, Document, Para, Proposition  # noqa: E402


# --------------------------------------------------------------------- parties
CASE = "Brightmarket Retail GmbH  v  Cobalt Cloud Analytics Ltd"
CLAIM_NO = "2026/0417 COM"
COURT = "Commercial Court (Ireland) — applying EU law"


# ----------------------------------------------------------------- EU acts (REAL)
# Real CELEX identifiers (verifiable in EU Cellar / EUR-Lex). ``in_data_eu`` is
# confirmed at build time against demo/data_eu.json; only 32004R0139 is present in
# that cached library subset, the rest are real Cellar CELEX ids outside it.
EU_ACTS: dict[str, dict] = {
    "32016R0679": {"title": "Regulation (EU) 2016/679 (General Data Protection Regulation)",
                   "short": "GDPR", "arts": "Arts 4(12), 22, 25, 28, 32, 33, 34, 44-49, 82, 94"},
    "31995L0046": {"title": "Directive 95/46/EC (Data Protection Directive)",
                   "short": "DP Directive (repealed)", "arts": "repealed by GDPR Art 94"},
    "32019L0770": {"title": "Directive (EU) 2019/770 (supply of digital content and services)",
                   "short": "Digital Content Directive", "arts": "Art 8 (conformity)"},
    "32019R1150": {"title": "Regulation (EU) 2019/1150 (fairness and transparency for "
                            "business users of online intermediation services)",
                   "short": "Platform-to-Business Regulation", "arts": "Art 3 (T&C changes)"},
    "32023R2854": {"title": "Regulation (EU) 2023/2854 (Data Act)",
                   "short": "Data Act", "arts": "Arts 23-26 (switching / portability)"},
    "32004R0139": {"title": "Council Regulation (EC) No 139/2004 (EC Merger Regulation)",
                   "short": "EU Merger Regulation", "arts": "Arts 1, 4 (thresholds / notification)"},
    "32021D0914": {"title": "Commission Implementing Decision (EU) 2021/914 (standard "
                            "contractual clauses for transfers to third countries)",
                   "short": "2021 SCCs", "arts": "Annex (Modules); cl 14 (transfer impact)"},
    "32010D0087": {"title": "Commission Decision 2010/87/EU (the 2010 standard "
                            "contractual clauses, controller-to-processor)",
                   "short": "2010 SCCs (repealed)", "arts": "repealed by Dec (EU) 2021/914"},
    "32002L0058": {"title": "Directive 2002/58/EC (ePrivacy / Privacy and Electronic "
                            "Communications Directive)",
                   "short": "ePrivacy Directive", "arts": "Art 5(3) (storage / access to terminal)"},
    "32024R1689": {"title": "Regulation (EU) 2024/1689 (Artificial Intelligence Act)",
                   "short": "AI Act", "arts": "Annex III; Arts 6, 113 (phased application)"},
    "32022L2555": {"title": "Directive (EU) 2022/2555 (measures for a high common level "
                            "of cybersecurity — NIS2)",
                   "short": "NIS2 Directive", "arts": "Arts 21, 23 (risk measures / incident reporting)"},
    "32022R2065": {"title": "Regulation (EU) 2022/2065 (Digital Services Act)",
                   "short": "Digital Services Act", "arts": "Arts 25, 27 (interface design / recommenders)"},
    "62018CJ0311": {"title": "Judgment in Case C-311/18 (Data Protection Commissioner v "
                             "Facebook Ireland and Schrems — 'Schrems II')",
                    "short": "Schrems II", "arts": "SCCs valid but require supplementary measures"},
}


# ------------------------------------------------------------------ propositions
def _p(pid: str, text: str) -> Proposition:
    return Proposition(pid, text, party="claimant", kind="allegation", burden="claimant")


PROPOSITIONS: list[Proposition] = [
    _p("P1", "Before contract Cobalt represented that the Platform was 'ISO 27001 certified "
             "and fully GDPR-compliant by design', and that representation was false."),
    _p("P2", "Cobalt processed Brightmarket's customer personal data for its own product / "
             "model-training purposes without instruction, contrary to its processor duty to "
             "act only on the controller's documented instructions (GDPR Art 28(3)(a))."),
    _p("P3", "The October 2025 personal-data breach exposed the personal data of "
             "approximately 2.3 million customers."),
    _p("P3b", "Even if only a fraction of records were exfiltrated, at least approximately 1.9 "
              "million records were 'exposed' within the meaning of GDPR Art 4(12)."),
    _p("P4", "Cobalt failed to notify the relevant supervisory authority of the breach within "
             "72 hours as required."),
    _p("P5", "The breach was caused solely by Cobalt's failure to implement appropriate "
             "technical and organisational measures (GDPR Art 32)."),
    _p("P6", "Cobalt's engineers left a production database publicly accessible on the "
             "internet for approximately three weeks before the breach."),
    _p("P7", "The Platform was not in conformity with the agreed specification: the analytics "
             "export module produced materially inaccurate revenue figures."),
    _p("P8", "Cobalt breached the data-transfer restrictions in Directive 95/46/EC (the "
             "standard incorporated by the 2017 DPA) by transferring data to a US sub-processor."),
    _p("P8b", "The transfers to Cobalt's US sub-processor were unlawful under GDPR Chapter V "
              "because the standard contractual clauses were not supplemented by adequate measures "
              "after Schrems II."),
    _p("P9", "Cobalt failed to maintain adequate backups, so data could not be restored after "
             "the breach."),
    _p("P9b", "A subset of Brightmarket's customer data was permanently lost in the October 2025 "
              "breach and could not be reconstructed."),
    _p("P10a", "Brightmarket suffered wasted expenditure of EUR 900,000, being subscription "
               "fees paid to Cobalt."),
    _p("P10b", "Brightmarket suffered loss of profit and further GDPR Art 82 / regulatory "
               "exposure of EUR 6,000,000 caused by the breach and outage."),
    _p("P11", "Cobalt's 2024 acquisition of Brightmarket's previous analytics supplier "
              "(NorthStar) was implemented without the required EU merger clearance, and Cobalt "
              "then degraded interoperability to lock Brightmarket in."),
    _p("P12", "Cobalt deployed an automated forecasting system that made decisions producing "
              "legal or similarly significant effects on Brightmarket's customers without the "
              "safeguards and transparency required (GDPR Art 22; the AI Act)."),
    _p("P13", "Cobalt caused non-essential analytics and tracking cookies to be set on "
              "Brightmarket's storefront without valid consent (ePrivacy Directive Art 5(3))."),
    _p("P14", "Cobalt failed to assist with, and itself failed to action, customers' data-subject "
              "access and erasure requests (GDPR Arts 12, 15 and 17)."),
]


# ------------------------------------------------------------------- gold oracle
# verdict + (doc_id, para) evidence anchors + legal_risk overlay + the *why* note.
# legal_risk vocabulary: NONE | CONTRACTUALLY_BARRED | SUPERSEDED | CAPPED |
# CAUSATION_PROBLEM | BURDEN_PROBLEM | TEMPORAL_SCOPE (new — a right that exists but
# whose statutory regime was not yet in application at the relevant time). The frontend
# renders any overlay string, so the new value is safe. ``acts`` lists REAL CELEX ids.
GOLD: dict[str, dict] = {
    "P1": {"verdict": "UNVERIFIED",
           "evidence": [("30", 2), ("27", 3), ("34", 3)], "contradicts": [],
           "legal_risk": "CONTRACTUALLY_BARRED", "acts": [],
           "note": "Genuinely unclear. A pre-contract sales email (doc 30) DID describe the "
                   "Platform as 'ISO 27001 certified and GDPR-compliant by design', so the "
                   "representation was made; but the surveillance-audit report (doc 27) shows "
                   "Cobalt WAS ISO 27001 certified for its core hosting at signing, the "
                   "certificate merely not yet extended to the analytics module — so falsity is "
                   "contested, not proven. Brightmarket's own due-diligence note (doc 34) records "
                   "that it verified and relied on a valid certificate, and MSA cl.24 (entire "
                   "agreement / non-reliance) would in any event bar reliance."},
    "P2": {"verdict": "SUPPORTED",
           "evidence": [("10", 2), ("14", 4)], "contradicts": [],
           "legal_risk": "NONE", "acts": ["32016R0679"],
           "note": "Cobalt's own internal email admits the merchant datasets (Brightmarket's "
                   "included) were used to train a forecasting model, and the DPIA records the "
                   "cross-use — a processor acting beyond the controller's documented instructions "
                   "(GDPR Art 28(3)(a)). The CTO's contrary account that 'only aggregated data' was "
                   "used is lower-weight witness evidence that does not displace the admission."},
    "P3": {"verdict": "CONTRADICTED",
           "evidence": [("19", 3), ("24", 3), ("16", 3)], "contradicts": [],
           "legal_risk": "CAUSATION_PROBLEM", "acts": ["32016R0679"],
           "note": "The DPO swears ~2.3m customers were exposed; BOTH forensic experts find only "
                   "~14,000 records were actually exfiltrated, and — fatally — Brightmarket's OWN "
                   "notification to the DPC put the affected population at ~19,000. The pleaded "
                   "2.3m figure is contradicted both by the experts and by the Claimant's own "
                   "regulatory filing (an own-goal)."},
    "P3b": {"verdict": "UNVERIFIED",
            "evidence": [("21", 5), ("19", 4), ("29", 4)], "contradicts": [],
            "legal_risk": "BURDEN_PROBLEM", "acts": ["32016R0679"],
            "note": "Murky and expert-split. Prof Strand (Claimant's expert) opines that up to "
                    "~1.9m records were 'accessible' and so 'exposed' within GDPR Art 4(12); Dr "
                    "Vale finds the pseudonymised remainder shows no evidence of access. The "
                    "access logs are incomplete for the window (doc 29), so neither 'exposed' nor "
                    "'not exposed' is made out. Survives the coherence solver but unproven — the "
                    "burden is the Claimant's."},
    "P4": {"verdict": "CONTRADICTED",
           "evidence": [("04", 9), ("08", 2), ("24", 2)], "contradicts": [],
           "legal_risk": "CONTRACTUALLY_BARRED", "acts": ["32016R0679", "32022L2555"],
           "note": "ALLOCATION TRAP: under GDPR Art 33(1) and DPA cl 9.2 it is the CONTROLLER "
                   "(Brightmarket) that must notify the supervisory authority within 72h; the "
                   "processor's duty (Art 33(2)) is only to notify the controller, which Cobalt did "
                   "within 18 hours. Brightmarket's own filing (doc 24) shows the controller "
                   "notified the DPC itself (on day 6, late) — the duty pleaded against Cobalt was "
                   "the Claimant's own. (Any parallel NIS2 incident-reporting duty is likewise the "
                   "entity's, not the processor's.)"},
    "P5": {"verdict": "CONTRADICTED",
           "evidence": [("12", 4), ("09", 2), ("17", 4), ("19", 7), ("21", 6)], "contradicts": [],
           "legal_risk": "CAUSATION_PROBLEM", "acts": ["32016R0679", "32022L2555"],
           "note": "OWN-GOAL + CONCURRENT CAUSATION. Brightmarket's own internal review admits its "
                   "admins disabled MFA against Cobalt's written guidance — a contributing cause "
                   "attributable to the Claimant — so 'caused SOLELY by Cobalt' cannot stand. The "
                   "murk: Prof Strand says Cobalt's flat network segmentation was ALSO a "
                   "substantial contributing cause (a live Art 32 failing), so an apportioned claim "
                   "could survive even though the pleaded 'sole cause' is contradicted."},
    "P6": {"verdict": "UNVERIFIED",
           "evidence": [("16", 6), ("26", 4), ("29", 5)], "contradicts": [],
           "legal_risk": "BURDEN_PROBLEM", "acts": ["32016R0679"],
           "note": "Thin and indirect. The DPO relays it second-hand ('I am told by our IT team…') "
                   "— hearsay. The pre-breach penetration test (doc 26) found an exposed staging "
                   "endpoint but could not confirm it was the PRODUCTION database or that it was "
                   "open for three weeks; the system logs (doc 29) show a misconfigured "
                   "security-group rule but retention gaps prevent confirming the duration. Neither "
                   "proven nor disproven — the burden is the Claimant's."},
    "P7": {"verdict": "SUPPORTED",
           "evidence": [("13", 3), ("19", 5)], "contradicts": [],
           "legal_risk": "NONE", "acts": ["32019L0770"],
           "note": "Genuine, evidence-backed point: the contemporaneous Defect Log and the "
                   "forensic expert both find the export module produced inaccurate revenue "
                   "figures — non-conformity (cf. Digital Content Directive (EU) 2019/770 Art 8)."},
    "P8": {"verdict": "CONTRADICTED",
           "evidence": [("07", 3)], "contradicts": [],
           "legal_risk": "SUPERSEDED", "acts": ["31995L0046", "32016R0679"],
           "note": "PARTIAL SUPERSESSION: the obligation pleaded rests on Directive 95/46/EC, "
                   "which the GDPR (Reg (EU) 2016/679, Art 94) repealed from 25 May 2018; the "
                   "parties' 2018 Addendum replaced that standard with the GDPR Chapter V regime. "
                   "The transfer point must be re-pleaded under the current law (see P8b)."},
    "P8b": {"verdict": "UNVERIFIED",
            "evidence": [("25", 3), ("11", 2), ("21", 7)], "contradicts": [],
            "legal_risk": "BURDEN_PROBLEM", "acts": ["32016R0679", "32021D0914", "32010D0087",
                                                      "62018CJ0311"],
            "note": "The re-pleadable transfer point, but unproven. The sub-processor schedule "
                    "(doc 25) records that standard contractual clauses WERE in place, and the 2021 "
                    "SCC Annex adopted the Commission Implementing Decision (EU) 2021/914 clauses, "
                    "replacing the repealed 2010/87/EU SCCs (a second partial supersession). After "
                    "Schrems II (C-311/18) SCCs may require supplementary measures, but the bundle "
                    "contains NO transfer impact assessment or record of such measures — so "
                    "unlawfulness is neither established nor excluded."},
    "P9": {"verdict": "CONTRADICTED",
           "evidence": [("31", 3), ("31", 2)], "contradicts": [],
           "legal_risk": "NONE", "acts": ["32016R0679"],
           "note": "Contradicted by the documents: the DR runbook records hourly snapshots with "
                   "30-day retention, and a 15 July 2025 restore test recovered 99.4% of data "
                   "within the recovery-time objective. 'Failed to maintain adequate backups' is "
                   "inconsistent with a documented, tested backup regime (GDPR Art 32(1)(c))."},
    "P9b": {"verdict": "UNVERIFIED",
            "evidence": [("31", 4), ("19", 8)], "contradicts": [],
            "legal_risk": "BURDEN_PROBLEM", "acts": ["32016R0679"],
            "note": "Thin and not tied to the breach. The 15 July restore test left ~0.6% "
                    "unrecovered (a known gap in a legacy index), but nothing ties that gap to the "
                    "October breach, and the forensic expert found restore was not in issue. "
                    "Permanent loss in this breach is unproven — survives but on the Claimant's "
                    "burden."},
    "P10a": {"verdict": "SUPPORTED",
             "evidence": [("20", 2), ("06", 2)], "contradicts": [],
             "legal_risk": "CAPPED", "acts": [],
             "note": "The Claimant's quantum expert (Caron) accepts the ~EUR 900k of subscription "
                     "fees as wasted expenditure — at/around the MSA cl.14 liability cap. The "
                     "Defendant's expert (Roos) would allow only ~EUR 450k, but that dispute goes "
                     "to amount, not to whether the head is made out."},
    "P10b": {"verdict": "CONTRADICTED",
             "evidence": [("20", 4), ("22", 4), ("20", 6), ("03", 14)], "contradicts": [],
             "legal_risk": "CAPPED", "acts": ["32016R0679"],
             "note": "Both quantum experts reject the EUR 6m figure — Caron supports ~EUR 1.1m, "
                     "Roos ~EUR 0.4m — and much of the Q4 downturn is attributed to a separate "
                     "ransomware event at the Claimant's logistics provider and to the market. MSA "
                     "cl.14 excludes consequential loss and caps liability near fees paid; GDPR "
                     "Art 82 compensation is a separate statutory head, apportioned for the "
                     "Claimant's contributory fault."},
    "P11": {"verdict": "CONTRADICTED",
            "evidence": [("15", 2), ("15", 4)], "contradicts": [],
            "legal_risk": "CONTRACTUALLY_BARRED", "acts": ["32004R0139", "32023R2854", "32019R1150"],
            "note": "The clearance memorandum records that the NorthStar acquisition fell below "
                    "the EU Merger Regulation (Reg (EC) No 139/2004) thresholds and was in any "
                    "event notified and cleared; the interoperability / lock-in complaint is "
                    "governed by the Data Act (Reg (EU) 2023/2854) and the P2B Regulation "
                    "(Reg (EU) 2019/1150), under which it is not pleaded."},
    "P12": {"verdict": "NOT_ADDRESSED",
            "evidence": [], "contradicts": [],
            "legal_risk": "TEMPORAL_SCOPE", "acts": ["32024R1689", "32016R0679", "32022R2065"],
            "note": "No document evidences any SOLELY automated decision producing legal or "
                    "similarly significant effects on a data subject (GDPR Art 22); the only "
                    "support is a programme lead's second-hand belief (hearsay, doc 18 ¶4). The "
                    "DPIA records the forecasting model as a B2B analytics aid, not an Annex III "
                    "high-risk AI system — and the AI Act's (Reg (EU) 2024/1689) high-risk "
                    "obligations apply on a phased timeline that had not begun at the October 2025 "
                    "breach. An evidence gap overlaid with a temporal-scope problem."},
    "P13": {"verdict": "UNVERIFIED",
            "evidence": [("32", 3), ("18", 5)], "contradicts": [],
            "legal_risk": "BURDEN_PROBLEM", "acts": ["32002L0058", "32016R0679"],
            "note": "Ambiguous and unattributed. The consent-configuration log (doc 32) shows a "
                    "consent banner WAS deployed but that, in a sample of sessions, some analytics "
                    "cookies fired before consent; it does not establish whether those cookies were "
                    "Cobalt's or Brightmarket's own tag manager. The only other support is the "
                    "programme lead's second-hand belief (hearsay). ePrivacy Art 5(3) consent is "
                    "engaged, but breach by Cobalt is unproven."},
    "P14": {"verdict": "NOT_ADDRESSED",
            "evidence": [("33", 3)], "contradicts": [],
            "legal_risk": "BURDEN_PROBLEM", "acts": ["32016R0679"],
            "note": "Unparticularised. The DSAR/erasure register (doc 33) records 412 requests, all "
                    "closed within statutory time, and no document identifies a single request that "
                    "Cobalt failed to assist with or action. Absence of evidence of a failure is an "
                    "evidence gap, not proof of one — the burden is the Claimant's."},
}

# Where each proposition is pleaded in the Particulars of Claim (doc 02).
PLEADED_AT: dict[str, tuple[str, int] | None] = {
    "P1": ("02", 7), "P2": ("02", 8), "P3": ("02", 9), "P3b": ("02", 10),
    "P4": ("02", 11), "P5": ("02", 12), "P6": ("02", 13), "P7": ("02", 14),
    "P8": ("02", 15), "P8b": ("02", 16), "P9": ("02", 17), "P9b": ("02", 18),
    "P10a": ("02", 19), "P10b": ("02", 19), "P11": ("02", 20), "P12": ("02", 21),
    "P13": ("02", 22), "P14": ("02", 23),
}


# ----------------------------------------------------------- document metadata
# id -> (title, doc_type, party, date, category, modality). ``category`` uses the
# frontend vocabulary; ``modality``/mime hints at the artefact kind.
DOC_META: dict[str, tuple] = {
    "01": ("Claim Form", "pleading", "claimant", "2026-02-10", "Pleading", "text"),
    "02": ("Particulars of Claim", "pleading", "claimant", "2026-02-10", "Pleading", "text"),
    "03": ("Master Subscription Agreement", "contract", "neutral", "2017-03-01", "Contract", "text"),
    "04": ("Data Processing Agreement", "contract", "neutral", "2017-03-01", "Contract", "text"),
    "05": ("Statement of Work", "contract", "neutral", "2017-03-01", "Contract", "text"),
    "06": ("Order Form", "contract", "neutral", "2024-04-15", "Contract", "text"),
    "07": ("Data Processing Addendum (GDPR, 2018)", "contract", "neutral", "2018-05-20", "Amendment", "text"),
    "08": ("Email — breach notification (Cobalt to Brightmarket)", "correspondence", "defendant", "2025-10-11", "Correspondence", "email"),
    "09": ("Email — security hardening guidance (Cobalt)", "correspondence", "defendant", "2025-06-03", "Correspondence", "email"),
    "10": ("Email — internal model-training note (Cobalt)", "correspondence", "neutral", "2025-02-18", "Correspondence", "email"),
    "11": ("International Transfer Annex / 2021 SCC Module", "contract", "neutral", "2021-11-30", "Amendment", "text"),
    "12": ("Internal Security Review (Brightmarket)", "record", "claimant", "2025-11-05", "Internal record", "text"),
    "13": ("Defect Log", "record", "neutral", "2025-09-20", "Record", "spreadsheet"),
    "14": ("Data Protection Impact Assessment", "record", "claimant", "2024-05-02", "Internal record", "text"),
    "15": ("Acquisition Clearance Memorandum", "record", "neutral", "2024-09-12", "Record", "text"),
    "16": ("Witness Statement — Lena Brandt (DPO, Brightmarket)", "witness", "claimant", "2026-03-15", "Witness (fact)", "text"),
    "17": ("Witness Statement — Tomas Reyes (Security Lead, Cobalt)", "witness", "defendant", "2026-03-20", "Witness (fact)", "text"),
    "18": ("Witness Statement — Anya Sorokin (Programme Lead, Brightmarket)", "witness", "claimant", "2026-03-18", "Witness (fact)", "text"),
    "19": ("Expert Report — Dr Idris Vale (Forensic / Security, jointly instructed)", "expert", "neutral", "2026-04-30", "Witness (expert)", "text"),
    "20": ("Expert Report — M. Caron (Quantum, Claimant-instructed)", "expert", "neutral", "2026-04-30", "Witness (expert)", "text"),
    "21": ("Expert Report — Prof. Helena Strand (Forensic / Security, Claimant-instructed)", "expert", "neutral", "2026-05-12", "Witness (expert)", "text"),
    "22": ("Expert Report — Dr Pieter Roos (Quantum, Defendant-instructed)", "expert", "neutral", "2026-05-12", "Witness (expert)", "text"),
    "23": ("Letter — Data Protection Commission (Ireland)", "correspondence", "neutral", "2025-12-02", "Regulatory", "letter"),
    "24": ("Breach Notification to the DPC (Brightmarket)", "record", "claimant", "2025-10-16", "Regulatory", "text"),
    "25": ("Sub-processor List & Transfer Schedule", "contract", "neutral", "2024-04-15", "Contract", "text"),
    "26": ("Penetration Test Report (pre-breach)", "record", "neutral", "2025-08-08", "Record", "text"),
    "27": ("Certification / Surveillance-Audit Report (ISO 27001)", "record", "neutral", "2016-11-20", "Record", "text"),
    "28": ("Witness Statement — Marcus Feld (CTO, Cobalt)", "witness", "defendant", "2026-03-22", "Witness (fact)", "text"),
    "29": ("Incident Timeline / System Logs (extract)", "record", "neutral", "2025-10-12", "Record", "text"),
    "30": ("Email thread — pre-contract sales correspondence", "correspondence", "neutral", "2016-12-05", "Correspondence", "email"),
    "31": ("Backup & Disaster-Recovery Runbook + Restore Test", "record", "neutral", "2025-07-15", "Record", "text"),
    "32": ("Cookie / Consent Configuration Log", "record", "neutral", "2025-09-01", "Record", "text"),
    "33": ("DSAR & Erasure Register (extract)", "record", "neutral", "2025-10-20", "Record", "text"),
    "34": ("Procurement Due-Diligence Note (Brightmarket)", "record", "claimant", "2016-12-20", "Internal record", "text"),
}


# --------------------------------------------------------------- bundle fixtures
# Only the cited paragraphs (plus a little context) are reproduced. Each (doc, n)
# anchor referenced by GOLD / PLEADED_AT / the recipes below appears here, so the
# engine loads a verbatim quote for every claim.
_PARAS: dict[str, list[tuple[int, str]]] = {
    "02": [
        (1, "The Claimant (\"Brightmarket\") is a company incorporated in Germany which operates "
            "online retail stores across several EU member states and is the controller of its "
            "customers' personal data."),
        (2, "The Defendant (\"Cobalt\") supplies a cloud analytics platform and acted as the "
            "Claimant's processor under a Data Processing Agreement."),
        (3, "By a Master Subscription Agreement, a Data Processing Agreement and a Statement of "
            "Work each dated 1 March 2017 the Claimant engaged the Defendant to host and analyse "
            "its customer and transaction data."),
        (7, "Before contract the Defendant represented that the Platform was ISO 27001 certified "
            "and fully GDPR-compliant by design. That representation was false."),
        (8, "The Defendant processed the Claimant's customer personal data for its own product "
            "and model-training purposes without the Claimant's instruction."),
        (9, "On or about 10 October 2025 a personal-data breach exposed the personal data of "
            "approximately 2.3 million of the Claimant's customers."),
        (10, "Further or alternatively, even if fewer records were exfiltrated, at least "
             "approximately 1.9 million records were exposed within the meaning of Article 4(12) "
             "of the GDPR."),
        (11, "The Defendant failed to notify the relevant supervisory authority of the breach "
             "within 72 hours as required."),
        (12, "The breach was caused solely by the Defendant's failure to implement appropriate "
             "technical and organisational measures."),
        (13, "The Defendant's engineers left a production database publicly accessible on the "
             "internet for approximately three weeks before the breach."),
        (14, "The Platform was not in conformity with the agreed specification: the analytics "
             "export module produced materially inaccurate revenue figures."),
        (15, "The Defendant transferred the Claimant's data to a sub-processor in the United "
             "States in breach of the data-transfer restrictions of Directive 95/46/EC as "
             "incorporated by the Data Processing Agreement."),
        (16, "Further or alternatively, the transfers to the United States sub-processor were "
             "unlawful under Chapter V of the GDPR because the standard contractual clauses were "
             "not supplemented by adequate measures following the Schrems II judgment."),
        (17, "The Defendant failed to maintain adequate backups, so the Claimant's data could "
             "not be restored after the breach."),
        (18, "Further or alternatively, a subset of the Claimant's customer data was permanently "
             "lost in the breach and could not be reconstructed."),
        (19, "The Claimant has suffered loss, namely wasted subscription fees of EUR 900,000 and "
             "loss of profit and further exposure of EUR 6,000,000."),
        (20, "The Defendant's 2024 acquisition of the Claimant's previous supplier, NorthStar, "
             "was implemented without the required merger clearance, and the Defendant thereafter "
             "degraded interoperability to lock the Claimant in."),
        (21, "The Defendant deployed an automated forecasting system that made decisions "
             "producing legal or similarly significant effects on the Claimant's customers "
             "without the safeguards and transparency required by law."),
        (22, "The Defendant caused non-essential analytics and tracking cookies to be set on the "
             "Claimant's storefront without the consent required by Article 5(3) of the ePrivacy "
             "Directive."),
        (23, "The Defendant failed to assist the Claimant with, and itself failed to action, the "
             "Claimant's customers' data-subject access and erasure requests."),
    ],
    "03": [
        (1, "This Master Subscription Agreement is made between Brightmarket Retail GmbH and "
            "Cobalt Cloud Analytics Ltd and is governed by the laws of Ireland."),
        (14, "Liability cap. Save for liability that cannot be excluded by law, the Supplier's "
             "total liability shall not exceed the fees paid in the 12 months preceding the "
             "claim, and the Supplier shall not be liable for loss of profit or other "
             "consequential loss."),
        (18, "Changes to platform terms, ranking and presentation are notified and governed in "
             "accordance with Regulation (EU) 2019/1150 (Platform-to-Business)."),
        (24, "Entire agreement. This Agreement is the entire agreement between the parties. Each "
             "party confirms it has not relied on any statement or representation not set out in "
             "this Agreement."),
    ],
    "04": [
        (1, "This Data Processing Agreement appoints the Supplier as processor of the customer "
            "personal data described in Schedule 1, the Customer being the controller."),
        (5, "The Processor shall process the personal data only on the documented instructions of "
            "the Controller (Article 28(3)(a) GDPR), and shall not use it for its own purposes."),
        (6, "The Processor shall assist the Controller, by appropriate technical and "
            "organisational measures, in responding to data-subject requests under Articles 12 to "
            "23 GDPR, including access and erasure requests."),
        (8, "The Processor shall implement appropriate technical and organisational measures "
            "(Article 32 GDPR). Configuration of multi-factor authentication on the Controller's "
            "administrator accounts is the Controller's responsibility (see SOW Annex B)."),
        (9, "Breach notification. The Controller shall notify the supervisory authority within 72 "
            "hours where required (Article 33(1) GDPR). The Processor shall notify the Controller "
            "without undue delay after becoming aware of a personal-data breach (Article 33(2))."),
        (12, "On termination the Processor shall make the data available for return or export via "
             "the self-service export API; switching and portability are governed by Regulation "
             "(EU) 2023/2854 (Data Act)."),
        (14, "Nothing in this Agreement limits a data subject's right to compensation under "
             "Article 82 GDPR, liability for which is apportioned according to each party's "
             "responsibility for the damage."),
    ],
    "05": [
        (1, "Statement of Work. The Supplier shall provide hosting, analytics and an export "
            "module to the specification in Annex A."),
        (3, "Annex B (shared responsibility): the Customer is responsible for enabling and "
            "enforcing multi-factor authentication on its own administrator accounts and for the "
            "configuration of its endpoint access controls."),
        (5, "Conformity of the digital service is assessed against the agreed specification and "
            "Directive (EU) 2019/770 (supply of digital content and digital services)."),
        (7, "The Customer operates and configures its own consent-management and tag-manager on "
            "the storefront; cookies and similar technologies are governed by Article 5(3) of "
            "Directive 2002/58/EC (ePrivacy) and the Customer's own cookie policy."),
    ],
    "06": [
        (1, "Order Form, dated 15 April 2024, for the Brightmarket subscription to the Cobalt "
            "Analytics Platform."),
        (2, "Annual subscription fee: EUR 900,000, payable in advance."),
    ],
    "07": [
        (1, "Data Processing Addendum, dated 20 May 2018, amending the 2017 Data Processing "
            "Agreement."),
        (2, "The parties record that the General Data Protection Regulation (Regulation (EU) "
            "2016/679) applies from 25 May 2018."),
        (3, "All references in the 2017 Agreement to Directive 95/46/EC are replaced: that "
            "Directive was repealed by Article 94 GDPR, and international transfers are henceforth "
            "governed by Chapter V of the GDPR and the Commission's standard contractual clauses."),
    ],
    "08": [
        (1, "From: Cobalt Security. To: Brightmarket DPO. Sent: 11 October 2025, 09:14. Subject: "
            "Personal-data breach notification."),
        (2, "We are notifying you, within 18 hours of becoming aware, of a personal-data breach "
            "affecting a subset of the customer dataset, so that you can assess notification to "
            "your supervisory authority. A forensic investigation is under way."),
    ],
    "09": [
        (1, "From: Cobalt Onboarding. To: Brightmarket IT. Sent: 3 June 2025. Subject: Security "
            "hardening — action required."),
        (2, "Please enable multi-factor authentication on all Brightmarket administrator accounts "
            "on the shared console; leaving MFA disabled materially increases the risk of "
            "credential compromise. This is the Customer's responsibility under SOW Annex B."),
    ],
    "10": [
        (1, "From: Cobalt Data Science. To: Cobalt Product (internal). Sent: 18 February 2025. "
            "Subject: forecasting model."),
        (2, "We're using the merchant datasets, including Brightmarket's, to train the new "
            "forecasting model. Legal said to get controller consent first but we shipped it to "
            "hit the release date."),
    ],
    "11": [
        (1, "International Transfer Annex, dated 30 November 2021, supplementing the Data "
            "Processing Agreement."),
        (2, "The parties adopt the standard contractual clauses set out in Commission "
            "Implementing Decision (EU) 2021/914, which replace the clauses annexed to Commission "
            "Decision 2010/87/EU; transfers in progress are to be migrated to the 2021 clauses by "
            "27 December 2022."),
        (4, "Where required, the parties shall carry out a transfer impact assessment and adopt "
            "supplementary measures consistent with the Schrems II judgment (Case C-311/18)."),
    ],
    "12": [
        (1, "Internal Security Review — Brightmarket, 5 November 2025 (privileged and "
            "confidential; prepared by the Claimant's security team)."),
        (4, "Finding: our administrators had disabled multi-factor authentication on the shared "
            "admin console in March 2025, contrary to Cobalt's written hardening guidance, and "
            "this materially contributed to the credential compromise behind the breach."),
        (5, "Recommendation: re-enable MFA immediately and review our own access-control "
            "configuration before attributing the incident externally."),
    ],
    "13": [
        (1, "Defect Log — Brightmarket / Cobalt Platform (extract)."),
        (3, "DEF-204 | Severity 2 | Export module: monthly revenue figures overstated by 4-9% "
            "for multi-currency stores; reconciliation mismatch confirmed and reproduced."),
    ],
    "14": [
        (1, "Data Protection Impact Assessment — Brightmarket analytics processing, 2 May 2024."),
        (4, "Processing note: the Supplier has indicated it may reuse aggregated and identifiable "
            "merchant datasets to improve and train its own analytics and forecasting models; "
            "this secondary use is outside the documented processing instructions and requires "
            "a controller decision."),
        (6, "Assessment: the forecasting model is a B2B analytics aid producing aggregate "
            "outputs; it is not, on present design, a solely automated decision affecting "
            "individual data subjects, nor an Annex III high-risk AI system, and the AI Act's "
            "high-risk obligations are not yet in application."),
    ],
    "15": [
        (1, "Acquisition Clearance Memorandum — Cobalt acquisition of NorthStar Analytics, "
            "12 September 2024."),
        (2, "The combined EU turnover of the parties fell below the thresholds of the EU Merger "
            "Regulation; the transaction was nonetheless notified to, and cleared by, the "
            "competent authority on 9 September 2024."),
        (4, "The transaction was assessed under Council Regulation (EC) No 139/2004 (the EU "
            "Merger Regulation); interoperability commitments were given and recorded."),
    ],
    "16": [
        (1, "Witness Statement of Lena Brandt, Data Protection Officer of Brightmarket. I make "
            "this statement from my own knowledge save where otherwise indicated."),
        (3, "From the customer database size at the time, I believe the breach exposed the "
            "personal data of approximately 2.3 million of our customers."),
        (6, "I am told by our IT team that Cobalt's engineers had left a production database "
            "publicly accessible on the internet for about three weeks before the breach; I did "
            "not see this myself."),
    ],
    "17": [
        (1, "Witness Statement of Tomas Reyes, Security Lead at Cobalt."),
        (4, "Our investigation traced the initial intrusion to a Brightmarket administrator "
            "account on which multi-factor authentication had been switched off on the customer "
            "side, despite our June 2025 guidance to enable it."),
    ],
    "18": [
        (1, "Witness Statement of Anya Sorokin, Programme Lead at Brightmarket."),
        (3, "After Cobalt acquired NorthStar I found it harder to export our data to alternative "
            "tools, and I considered we were being locked into the Cobalt platform."),
        (4, "I understand that the forecasting model was used to make automated decisions about "
            "individual customers, although I was not involved in that workstream and did not see "
            "it operate."),
        (5, "I am told by our marketing team that Cobalt's scripts set tracking cookies on the "
            "storefront without consent; I have not reviewed the configuration myself."),
    ],
    "19": [
        (1, "Expert Report of Dr Idris Vale, instructed jointly on forensic and security issues."),
        (3, "On the forensic evidence, approximately 14,000 customer records were actually "
            "exfiltrated. The remainder of the dataset was pseudonymised at rest and shows no "
            "evidence of access; the figure of 2.3 million is not supported by the logs."),
        (4, "In my opinion the pseudonymised remainder cannot be said to have been 'exposed': "
            "there is no log evidence of read access to it, and pseudonymisation materially "
            "reduced the risk to those data subjects."),
        (5, "The export module did produce materially inaccurate revenue figures for "
            "multi-currency stores; in my opinion this is a genuine non-conformity with the "
            "agreed specification."),
        (7, "The proximate cause of the intrusion was a compromised administrator credential on "
            "an account where MFA had been disabled by the Customer; this was a substantial "
            "contributing cause of the breach."),
        (8, "I found no evidence that any breached data was unrecoverable; restoration of the "
            "affected records was not, on the material I reviewed, in issue."),
    ],
    "20": [
        (1, "Expert Report of M. Caron on quantum, instructed by the Claimant."),
        (2, "I accept that the EUR 900,000 of subscription fees can properly be characterised as "
            "wasted expenditure."),
        (4, "The claimed EUR 6,000,000 is not supported. On my analysis the supportable loss of "
            "profit is of the order of EUR 1.1 million."),
        (6, "A significant part of the Q4 downturn is attributable to a separate ransomware "
            "incident affecting the Claimant's own logistics provider and to wider market "
            "conditions, not to the Platform."),
    ],
    "21": [
        (1, "Expert Report of Prof. Helena Strand, instructed by the Claimant on forensic and "
            "security issues."),
        (4, "I agree with Dr Vale that around 14,000 records were exfiltrated. However, in my "
            "opinion the population whose data was accessible during the incident window was much "
            "larger, and 'exposure' should not be equated with confirmed exfiltration."),
        (5, "On my reconstruction up to approximately 1.9 million records were potentially "
            "accessible to the intruder and so, in my view, 'exposed' within Article 4(12) GDPR; "
            "I accept the available logs do not place this beyond doubt."),
        (6, "In my opinion Cobalt's network was insufficiently segmented, which allowed lateral "
            "movement after the initial compromise; this was a substantial contributing cause of "
            "the breach independent of the disabled MFA."),
        (7, "Standard contractual clauses alone may not suffice for transfers to the United "
            "States after Schrems II; I have not, however, seen a transfer impact assessment or "
            "evidence of supplementary measures either way."),
    ],
    "22": [
        (1, "Expert Report of Dr Pieter Roos on quantum, instructed by the Defendant."),
        (2, "In my view only about EUR 450,000 of the fees can be treated as wasted: the Platform "
            "delivered usable analytics for much of the subscription period."),
        (4, "I agree the EUR 6,000,000 is unsupported. On my analysis any recoverable loss of "
            "profit is no more than about EUR 0.4 million, once the ransomware incident and "
            "market conditions are removed."),
    ],
    "23": [
        (1, "Data Protection Commission (Ireland) — letter to Brightmarket Retail GmbH, "
            "2 December 2025."),
        (2, "We acknowledge receipt of your breach notification under Article 33 GDPR. We note "
            "that notification was made outside the 72-hour period and that, on your account, the "
            "processor had informed you of the breach without undue delay; our assessment of "
            "controller and processor responsibilities is ongoing."),
    ],
    "24": [
        (1, "Personal-data breach notification by Brightmarket Retail GmbH (controller) to the "
            "Data Protection Commission, submitted 16 October 2025."),
        (2, "We became aware of the breach via our processor's notification on 11 October 2025 "
            "and are notifying your office on 16 October 2025; we recognise this is beyond the "
            "72-hour period and explain the delay below."),
        (3, "On our current assessment the breach affected approximately 19,000 data subjects "
            "whose records were confirmed to have been accessed; investigation continues."),
    ],
    "25": [
        (1, "Sub-processor List and Transfer Schedule (Schedule 3 to the DPA, updated "
            "15 April 2024)."),
        (3, "Cobalt Analytics Inc. (United States) is engaged as a sub-processor for elastic "
            "compute; transfers to it are made under the standard contractual clauses, which are "
            "in place and incorporated by the International Transfer Annex."),
    ],
    "26": [
        (1, "Penetration Test Report — Brightmarket / Cobalt environment, 8 August 2025 "
            "(commissioned jointly)."),
        (4, "Finding PT-07 (Medium): a staging endpoint was reachable from the public internet "
            "during testing. We were unable to confirm whether this endpoint exposed the "
            "production database, or for how long it had been reachable; remediation was advised."),
    ],
    "27": [
        (1, "ISO 27001 Surveillance-Audit Report — Cobalt Cloud Analytics Ltd, 20 November 2016 "
            "(issued by the certification body)."),
        (3, "At the date of audit Cobalt held a valid ISO 27001 certificate covering its core "
            "hosting and platform operations; the analytics-export module was scheduled for "
            "inclusion at the next surveillance cycle and was not yet within the certified scope."),
    ],
    "28": [
        (1, "Witness Statement of Marcus Feld, Chief Technology Officer of Cobalt."),
        (3, "Our ISO 27001 certificate was valid for the contracted hosting services throughout, "
            "and our pre-contract materials reflected that certified scope."),
        (4, "The forecasting work used aggregated and de-identified datasets; to my knowledge it "
            "did not use identifiable Brightmarket customer records for training."),
    ],
    "29": [
        (1, "Incident Timeline and System Logs (extract), compiled 12 October 2025."),
        (4, "Access logging for the affected storage tier was incomplete for part of the incident "
            "window owing to a log-rotation gap; the number of records actually read cannot be "
            "determined from the available logs."),
        (5, "A security-group rule permitting inbound access from any address was present on a "
            "staging subnet; the change history needed to establish how long it had been in place "
            "had been truncated by retention limits."),
    ],
    "30": [
        (1, "Email thread — Cobalt Sales to Brightmarket Procurement, 5 December 2016 "
            "(pre-contract)."),
        (2, "To answer your security questionnaire: the Platform is ISO 27001 certified and "
            "GDPR-compliant by design, and we would be happy to share our certificate."),
    ],
    "31": [
        (1, "Backup & Disaster-Recovery Runbook and Restore-Test Record, 15 July 2025."),
        (2, "Backups: hourly snapshots of the production data stores are taken and retained for "
            "30 days, with daily off-region copies."),
        (3, "Restore test of 15 July 2025: a full restore from snapshot recovered 99.4% of the "
            "test dataset within the four-hour recovery-time objective."),
        (4, "The 0.6% not recovered relates to a known indexing gap in a legacy table flagged for "
            "decommissioning; it is unrelated to any specific incident."),
    ],
    "32": [
        (1, "Cookie / Consent Configuration Log — Brightmarket storefront, 1 September 2025."),
        (3, "A consent banner was active. In a sample of 1,000 sessions, a small number of "
            "analytics cookies were observed to fire before consent was recorded; the log does not "
            "attribute these to a specific script owner (Cobalt tag or the Customer's own tag "
            "manager)."),
    ],
    "33": [
        (1, "DSAR & Erasure Register (extract) — Brightmarket, to 20 October 2025."),
        (3, "412 data-subject access and erasure requests were received in the period; all are "
            "recorded as closed within the statutory time limit. No request is recorded as refused "
            "or unactioned by the processor."),
    ],
    "34": [
        (1, "Procurement Due-Diligence Note — Brightmarket, 20 December 2016 (internal)."),
        (3, "We verified Cobalt's ISO 27001 certificate and reviewed the certified scope before "
            "signing; we are satisfied to rely on it for the hosting services we are procuring."),
    ],
}


def bundle() -> Bundle:
    """A `Bundle` of the synthetic fixtures — lets the real coherence engine load a
    verbatim quote for every cited anchor (no quote is ever invented)."""
    docs: list[Document] = []
    for doc_id, (title, doc_type, party, date, _cat, _mod) in DOC_META.items():
        paras = [Para(n, t) for n, t in _PARAS.get(doc_id, [])]
        if not paras:
            continue
        docs.append(Document(id=doc_id, title=title, doc_type=doc_type,
                             party=party, date=date, paras=paras))
    docs.sort(key=lambda d: d.id)
    return Bundle(docs=docs)


# --------------------------------------------------------------------- recipes
# Same shape as src/coherence.py ``_RECIPES`` (issue/story/amendments/claims/edges),
# so the real brute-force solver can consume them via coherence._build_claim. The
# truth-bearing labels (verdict, overlay, why-note, pleaded location) come from GOLD /
# PLEADED_AT above — reuse, not duplication.
#
# Design contract for solver/verdict consistency:
#   * CONTRADICTED propositions carry a HARD contradicts/supersedes edge from a
#     higher-weight bundle/legal claim onto the pleaded claim, so the solver rejects it.
#   * SUPPORTED / UNVERIFIED / NOT_ADDRESSED propositions carry only SOFT edges onto the
#     pleaded claim (supports / qualifies / attacks / caps / legal_bar), so it stays
#     accepted — "survives the coherent story" — while the gold verdict records that it
#     is unproven (UNVERIFIED), an evidence gap (NOT_ADDRESSED) or genuinely made out
#     (SUPPORTED). Hard edges between two *bundle* claims (e.g. expert vs witness) are
#     fine and let the solver pick the heavier evidence.
RECIPES: list[dict] = [
    {
        "issue": "REPRESENTATION/NON_RELIANCE",
        "story": [
            "A pre-contract sales email did describe the Platform as 'ISO 27001 certified and "
            "GDPR-compliant by design', so the representation was made.",
            "But the surveillance-audit report shows Cobalt held a valid ISO 27001 certificate "
            "for its core hosting at signing — only the analytics module was outside scope.",
            "Brightmarket's own due-diligence note records that it verified and relied on a valid "
            "certificate (an own-goal on falsity).",
            "MSA cl.24 (entire agreement / non-reliance) would in any event bar reliance.",
            "Falsity is therefore genuinely unclear, not proven.",
        ],
        "amendments": [
            "Do not plead the representation as simply 'false': particularise which certified "
            "scope was misstated, and address the non-reliance clause and Brightmarket's own "
            "reliance on a verified certificate. Lawyer review required.",
        ],
        "claims": [
            {"id": "p1_rep", "kind": "pleading", "prop": "P1",
             "text": "Pre-contract representation that the Platform was ISO 27001 certified and "
                     "GDPR-compliant by design, false."},
            {"id": "sales_rep", "kind": "bundle", "anchor": ("30", 2),
             "source_type": "contemporaneous_email",
             "text": "Pre-contract sales email: 'the Platform is ISO 27001 certified and "
                     "GDPR-compliant by design'."},
            {"id": "audit_partial", "kind": "bundle", "anchor": ("27", 3), "source_type": "expert_report",
             "text": "Surveillance-audit report: valid ISO 27001 certificate for core hosting at "
                     "signing; analytics module not yet in certified scope."},
            {"id": "procurement_note", "kind": "bundle", "anchor": ("34", 3), "source_type": "admission",
             "text": "Brightmarket's own procurement note: it verified Cobalt's ISO 27001 "
                     "certificate and was satisfied to rely on it."},
            {"id": "cto_cert", "kind": "bundle", "anchor": ("28", 3), "source_type": "witness_statement",
             "text": "Cobalt CTO: the certificate was valid for the contracted hosting services."},
            {"id": "nonreliance_cl24", "kind": "legal_overlay", "anchor": ("03", 24),
             "source_type": "legal_clause",
             "text": "MSA cl.24 (entire agreement / non-reliance) bars reliance on pre-contract "
                     "representations."},
        ],
        "edges": [
            {"source": "sales_rep", "target": "p1_rep", "relation": "supports", "hard": False,
             "rule": "email_evidences_representation_made",
             "explanation": "The sales email shows the representation was in fact made."},
            {"source": "audit_partial", "target": "p1_rep", "relation": "qualifies", "hard": False,
             "rule": "partial_truth_qualifies_falsity",
             "explanation": "A valid certificate for core hosting makes the falsity partial and "
                            "contested, not clear-cut."},
            {"source": "procurement_note", "target": "p1_rep", "relation": "attacks", "hard": False,
             "rule": "own_diligence_relied_on_valid_cert",
             "explanation": "The Claimant's own diligence verified a valid certificate — an "
                            "own-goal cutting against 'the representation was false'."},
            {"source": "cto_cert", "target": "p1_rep", "relation": "attacks", "hard": False,
             "rule": "defendant_witness_cert_valid",
             "explanation": "The CTO says the certificate was valid for the contracted scope."},
            {"source": "nonreliance_cl24", "target": "p1_rep", "relation": "legal_bar", "hard": False,
             "rule": "non_reliance_legal_bar",
             "explanation": "A non-reliance clause is a legal blocker, not a factual contradiction."},
        ],
    },
    {
        "issue": "PURPOSE_LIMITATION",
        "story": [
            "Cobalt's own internal email admits the merchant datasets, Brightmarket's included, "
            "were used to train its forecasting model.",
            "The DPIA independently records the secondary cross-use as outside instructions.",
            "The CTO says only aggregated data was used — but that lower-weight witness account "
            "does not displace the contemporaneous admission.",
            "A processor acting beyond the controller's documented instructions breaches "
            "GDPR Art 28(3)(a) — the allegation is supported.",
        ],
        "amendments": [
            "Keep the purpose-limitation allegation (P2) — it is the Claimant's strongest, "
            "admission-backed point; be ready to meet the 'aggregated data only' defence.",
        ],
        "claims": [
            {"id": "p2_purpose", "kind": "pleading", "prop": "P2",
             "text": "Cobalt processed the data for its own model-training without instruction "
                     "(GDPR Art 28(3)(a))."},
            {"id": "training_admission", "kind": "bundle", "anchor": ("10", 2),
             "source_type": "admission",
             "text": "Cobalt internal email admits training a forecasting model on the merchant "
                     "datasets without controller consent."},
            {"id": "dpia_crossuse", "kind": "bundle", "anchor": ("14", 4), "source_type": "defect_log",
             "text": "The DPIA records the secondary cross-use as outside the documented "
                     "processing instructions."},
            {"id": "cto_aggregated", "kind": "bundle", "anchor": ("28", 4), "source_type": "witness_statement",
             "text": "Cobalt CTO: the forecasting work used aggregated / de-identified data, not "
                     "identifiable customer records."},
            {"id": "art28_overlay", "kind": "legal_overlay", "anchor": ("04", 5),
             "source_type": "legal_clause",
             "text": "GDPR Art 28(3)(a) / DPA cl.5: process only on the controller's documented "
                     "instructions."},
        ],
        "edges": [
            {"source": "training_admission", "target": "p2_purpose", "relation": "supports", "hard": False,
             "rule": "admission_supports_purpose_breach",
             "explanation": "Cobalt's own admission supports the unlawful secondary processing."},
            {"source": "dpia_crossuse", "target": "p2_purpose", "relation": "supports", "hard": False,
             "rule": "dpia_supports_purpose_breach",
             "explanation": "The DPIA independently records the cross-use."},
            {"source": "cto_aggregated", "target": "p2_purpose", "relation": "attacks", "hard": False,
             "rule": "aggregated_data_defence",
             "explanation": "The CTO's 'aggregated only' account is a lower-weight witness "
                            "challenge that does not displace the contemporaneous admission."},
            {"source": "art28_overlay", "target": "p2_purpose", "relation": "supports", "hard": False,
             "rule": "art28_instruction_standard",
             "explanation": "Art 28(3)(a) sets the documented-instruction standard the conduct breaches."},
        ],
    },
    {
        "issue": "BREACH_SCALE",
        "story": [
            "The DPO swears approximately 2.3 million customers were exposed.",
            "Both forensic experts find only about 14,000 records were actually exfiltrated.",
            "Brightmarket's OWN notification to the DPC put the affected population at ~19,000.",
            "The pleaded 2.3m figure is contradicted by the experts and by the Claimant's own "
            "regulatory filing — an own-goal.",
        ],
        "amendments": [
            "Do not plead the 2.3m figure: it is contradicted by both experts and by the "
            "Claimant's own DPC notification (~19,000). Plead the confirmed-affected figure.",
        ],
        "claims": [
            {"id": "p3_scale", "kind": "pleading", "prop": "P3",
             "text": "The breach exposed the personal data of approximately 2.3 million customers."},
            {"id": "dpo_23m", "kind": "bundle", "anchor": ("16", 3), "source_type": "witness_statement",
             "text": "DPO: approximately 2.3 million customers were exposed (belief from database size)."},
            {"id": "vale_14k", "kind": "bundle", "anchor": ("19", 3), "source_type": "expert_report",
             "text": "Forensic expert (Vale): about 14,000 records actually exfiltrated; the 2.3m "
                     "figure is unsupported by the logs."},
            {"id": "dpc_filing_19k", "kind": "bundle", "anchor": ("24", 3), "source_type": "admission",
             "text": "Brightmarket's OWN DPC breach notification: approximately 19,000 data "
                     "subjects confirmed affected."},
            {"id": "strand_accessible", "kind": "bundle", "anchor": ("21", 4), "source_type": "expert_report",
             "text": "Forensic expert (Strand): agrees ~14,000 exfiltrated, but argues a larger "
                     "set was 'accessible' — still not 2.3m."},
        ],
        "edges": [
            {"source": "vale_14k", "target": "p3_scale", "relation": "contradicts", "hard": True,
             "rule": "numeric_interval_disjoint",
             "explanation": "The forensic ~14,000 is disjoint from the pleaded ~2.3 million."},
            {"source": "dpc_filing_19k", "target": "p3_scale", "relation": "contradicts", "hard": True,
             "rule": "own_regulatory_filing_contradicts_pleaded_scale",
             "explanation": "The Claimant's own DPC filing (~19,000) is disjoint from the pleaded "
                            "2.3 million — an own-goal."},
            {"source": "vale_14k", "target": "dpo_23m", "relation": "contradicts", "hard": True,
             "rule": "expert_displaces_witness_estimate",
             "explanation": "The forensic finding displaces the DPO's untested estimate "
                            "(witness-vs-expert conflict)."},
            {"source": "dpc_filing_19k", "target": "dpo_23m", "relation": "contradicts", "hard": True,
             "rule": "own_filing_displaces_own_witness",
             "explanation": "The Claimant's own filing (~19,000) displaces its own DPO's 2.3m "
                            "estimate."},
            {"source": "strand_accessible", "target": "p3_scale", "relation": "qualifies", "hard": False,
             "rule": "claimants_own_expert_will_not_support_23m",
             "explanation": "Even the Claimant's own expert will not support 2.3m — she speaks of "
                            "accessibility, not 2.3 million exposed."},
        ],
    },
    {
        "issue": "EXPOSURE_DEFINITION",
        "story": [
            "Strand opines that up to ~1.9m records were 'accessible' and so 'exposed' within "
            "GDPR Art 4(12).",
            "Vale finds the pseudonymised remainder shows no evidence of access — not 'exposed'.",
            "The access logs are incomplete for the window, so neither side is made out.",
            "The 1.9m exposure point survives the coherent story but is unproven.",
        ],
        "amendments": [
            "If pursuing the 1.9m 'exposure' case, obtain the missing access logs or a "
            "reconstruction that places it beyond doubt; the experts diverge and the logs are "
            "incomplete. Lawyer review required.",
        ],
        "claims": [
            {"id": "p3b_exposed", "kind": "pleading", "prop": "P3b",
             "text": "At least ~1.9 million records were 'exposed' within GDPR Art 4(12)."},
            {"id": "strand_19m", "kind": "bundle", "anchor": ("21", 5), "source_type": "expert_report",
             "text": "Strand: up to ~1.9m records potentially accessible and so 'exposed' within "
                     "Art 4(12); accepts the logs do not place it beyond doubt."},
            {"id": "vale_noaccess", "kind": "bundle", "anchor": ("19", 4), "source_type": "expert_report",
             "text": "Vale: the pseudonymised remainder shows no log evidence of access and "
                     "cannot be said to have been 'exposed'."},
            {"id": "logs_incomplete", "kind": "bundle", "anchor": ("29", 4), "source_type": "defect_log",
             "text": "System logs: access logging was incomplete for part of the window; records "
                     "actually read cannot be determined."},
            {"id": "absence_access", "kind": "absence",
             "text": "No definitive access-log evidence quantifies the 'exposed' set either way."},
        ],
        "edges": [
            {"source": "strand_19m", "target": "p3b_exposed", "relation": "supports", "hard": False,
             "rule": "claimant_expert_supports_exposure",
             "explanation": "The Claimant's expert supports a ~1.9m 'exposed' population."},
            {"source": "vale_noaccess", "target": "p3b_exposed", "relation": "attacks", "hard": False,
             "rule": "no_access_evidence_attacks_exposure",
             "explanation": "Vale finds no evidence of access to the remainder — undermining "
                            "'exposed'."},
            {"source": "logs_incomplete", "target": "p3b_exposed", "relation": "qualifies", "hard": False,
             "rule": "incomplete_logs_leave_it_open",
             "explanation": "Incomplete logs leave the exposed-set size genuinely open."},
            {"source": "absence_access", "target": "p3b_exposed", "relation": "qualifies", "hard": False,
             "rule": "absence_of_quantifying_evidence",
             "explanation": "Absence of quantifying evidence keeps the point unproven, not "
                            "contradicted."},
        ],
    },
    {
        "issue": "BREACH_NOTIFICATION",
        "story": [
            "The pleading reads as 'Cobalt never notified the regulator' — an apparent gap.",
            "But GDPR Art 33(1) and DPA cl 9.2 put 72-hour notification to the supervisory "
            "authority on the CONTROLLER (Brightmarket).",
            "The processor's duty (Art 33(2)) is to notify the controller, which Cobalt did "
            "within 18 hours.",
            "Brightmarket's own filing shows the controller notified the DPC itself, on day 6 — "
            "the duty pleaded against Cobalt was the Claimant's own.",
        ],
        "amendments": [
            "Withdraw the 72-hour allegation against the processor: the supervisory-authority "
            "duty is allocated to the controller by GDPR Art 33(1) and DPA cl 9.2, and the "
            "Claimant's own filing shows it notified (late) itself.",
        ],
        "claims": [
            {"id": "p4_notify", "kind": "pleading", "prop": "P4",
             "text": "Cobalt failed to notify the supervisory authority within 72 hours."},
            {"id": "dpa_alloc_cl92", "kind": "legal_overlay", "anchor": ("04", 9),
             "source_type": "legal_clause",
             "text": "DPA cl 9.2 / GDPR Art 33: the CONTROLLER notifies the supervisory authority "
                     "within 72h; the processor notifies the controller without undue delay."},
            {"id": "cobalt_notice", "kind": "bundle", "anchor": ("08", 2),
             "source_type": "contemporaneous_email",
             "text": "Cobalt notified Brightmarket of the breach within 18 hours."},
            {"id": "bm_late_filing", "kind": "bundle", "anchor": ("24", 2), "source_type": "admission",
             "text": "Brightmarket's own filing: the controller notified the DPC on day 6, beyond "
                     "the 72-hour period."},
            {"id": "dpc_letter", "kind": "bundle", "anchor": ("23", 2), "source_type": "contemporaneous_email",
             "text": "DPC letter: notification was late, and the processor had informed the "
                     "controller without undue delay."},
        ],
        "edges": [
            {"source": "dpa_alloc_cl92", "target": "p4_notify", "relation": "contradicts", "hard": True,
             "rule": "responsibility_allocated_to_claimant",
             "explanation": "The 72-hour supervisory-authority duty is allocated to the controller; "
                            "the allegation mis-assigns it to the processor (an allocation trap)."},
            {"source": "cobalt_notice", "target": "p4_notify", "relation": "attacks", "hard": False,
             "rule": "processor_duty_discharged",
             "explanation": "Cobalt discharged its Art 33(2) duty by notifying the controller in 18h."},
            {"source": "bm_late_filing", "target": "p4_notify", "relation": "attacks", "hard": False,
             "rule": "controller_notified_itself_late",
             "explanation": "The Claimant's own filing shows the controller carried (and missed) "
                            "the 72h duty — an own-goal."},
            {"source": "dpc_letter", "target": "p4_notify", "relation": "qualifies", "hard": False,
             "rule": "regulator_records_processor_timely",
             "explanation": "The DPC's letter records the processor informed the controller "
                            "without undue delay."},
        ],
    },
    {
        "issue": "TOMS/CAUSATION",
        "story": [
            "P5 alleges the breach was caused solely by Cobalt's failure of GDPR Art 32 measures.",
            "Brightmarket's OWN internal security review finds its admins disabled MFA against "
            "Cobalt's written guidance — a contributing cause attributable to the Claimant.",
            "Vale puts the proximate cause on that disabled-MFA account.",
            "But Strand says Cobalt's flat network segmentation was ALSO a substantial "
            "contributing cause — concurrent causation.",
            "So 'caused solely by Cobalt' cannot stand, though an apportioned claim is live.",
        ],
        "amendments": [
            "Withdraw 'caused solely by Cobalt': the Claimant's own review admits a contributing "
            "cause (disabled MFA). Plead apportionment, and rely on Strand's segmentation point "
            "for Cobalt's share.",
        ],
        "claims": [
            {"id": "p5_solecause", "kind": "pleading", "prop": "P5",
             "text": "The breach was caused solely by Cobalt's failure of Art 32 measures."},
            {"id": "internal_review", "kind": "bundle", "anchor": ("12", 4), "source_type": "admission",
             "text": "Brightmarket's own internal review: its admins disabled MFA against Cobalt's "
                     "guidance, materially contributing to the breach."},
            {"id": "hardening_email", "kind": "bundle", "anchor": ("09", 2),
             "source_type": "contemporaneous_email",
             "text": "Cobalt advised Brightmarket in writing to enable administrator MFA."},
            {"id": "reyes_cause", "kind": "bundle", "anchor": ("17", 4), "source_type": "witness_statement",
             "text": "Cobalt's security lead traced the intrusion to a customer account with MFA "
                     "switched off."},
            {"id": "vale_proximate", "kind": "bundle", "anchor": ("19", 7), "source_type": "expert_report",
             "text": "Vale: proximate cause was a compromised credential on the MFA-disabled "
                     "account — a substantial contributing cause."},
            {"id": "strand_segmentation", "kind": "bundle", "anchor": ("21", 6), "source_type": "expert_report",
             "text": "Strand: Cobalt's insufficient network segmentation allowed lateral movement "
                     "— a substantial contributing cause independent of the MFA."},
            {"id": "art32_overlay", "kind": "legal_overlay", "anchor": ("04", 8),
             "source_type": "legal_clause",
             "text": "GDPR Art 32 / DPA cl 8: administrator-MFA configuration is the controller's "
                     "responsibility (SOW Annex B)."},
        ],
        "edges": [
            {"source": "internal_review", "target": "p5_solecause", "relation": "contradicts", "hard": True,
             "rule": "own_document_contradicts_sole_cause",
             "explanation": "The Claimant's own review admits a contributing cause it caused — an own goal."},
            {"source": "hardening_email", "target": "p5_solecause", "relation": "attacks", "hard": False,
             "rule": "claimant_was_warned",
             "explanation": "Cobalt had advised enabling MFA; the omission was the Claimant's."},
            {"source": "reyes_cause", "target": "p5_solecause", "relation": "attacks", "hard": False,
             "rule": "alternative_causation",
             "explanation": "The intrusion traced to the customer's disabled-MFA account."},
            {"source": "vale_proximate", "target": "p5_solecause", "relation": "attacks", "hard": False,
             "rule": "expert_proximate_cause_is_mfa",
             "explanation": "Vale puts the proximate cause on the Customer's disabled MFA."},
            {"source": "strand_segmentation", "target": "p5_solecause", "relation": "qualifies", "hard": False,
             "rule": "concurrent_cobalt_segmentation_failing",
             "explanation": "Strand identifies a concurrent Cobalt failing — so causation is "
                            "shared, not 'solely Cobalt' and not 'solely the Claimant'."},
            {"source": "art32_overlay", "target": "p5_solecause", "relation": "qualifies", "hard": False,
             "rule": "shared_responsibility_overlay",
             "explanation": "MFA configuration was allocated to the controller — shared responsibility."},
        ],
    },
    {
        "issue": "PUBLIC_EXPOSURE/HEARSAY",
        "story": [
            "P6 (a production database left publicly accessible for ~3 weeks) rests on the DPO "
            "relaying 'I am told by our IT team…' — hearsay.",
            "The pre-breach penetration test found an exposed staging endpoint, but could not "
            "confirm it was the production database or for how long.",
            "The system logs show a misconfigured security-group rule, but retention gaps prevent "
            "confirming the three-week duration.",
            "So the allegation is unverified, not proven — a burden / admissibility gap.",
        ],
        "amendments": [
            "Do not plead the public-exposure allegation on hearsay plus ambiguous test/log "
            "findings; obtain the underlying configuration history and first-hand evidence. "
            "Lawyer review required.",
        ],
        "claims": [
            {"id": "p6_exposed", "kind": "pleading", "prop": "P6",
             "text": "Cobalt left a production database publicly accessible for ~3 weeks."},
            {"id": "dpo_hearsay", "kind": "bundle", "anchor": ("16", 6), "source_type": "witness_statement",
             "text": "DPO relays, second-hand ('I am told by our IT team…'), that a database was "
                     "left publicly accessible — hearsay, no personal knowledge."},
            {"id": "pentest_endpoint", "kind": "bundle", "anchor": ("26", 4), "source_type": "defect_log",
             "text": "Penetration test: a staging endpoint was reachable from the internet, but it "
                     "could not be confirmed as the production database or for how long."},
            {"id": "logs_window", "kind": "bundle", "anchor": ("29", 5), "source_type": "defect_log",
             "text": "System logs: an open security-group rule existed on a staging subnet, but "
                     "retention truncation prevents establishing the duration."},
            {"id": "absence_exposure", "kind": "absence",
             "text": "No contemporaneous ticket or log confirms a PRODUCTION database publicly "
                     "accessible for ~3 weeks."},
        ],
        "edges": [
            {"source": "dpo_hearsay", "target": "p6_exposed", "relation": "qualifies", "hard": False,
             "rule": "uncorroborated_hearsay",
             "explanation": "The headline support is uncorroborated hearsay — weight reduced."},
            {"source": "pentest_endpoint", "target": "p6_exposed", "relation": "qualifies", "hard": False,
             "rule": "ambiguous_pentest_finding",
             "explanation": "The pentest finding is consistent with, but does not establish, the "
                            "pleaded production-database exposure."},
            {"source": "logs_window", "target": "p6_exposed", "relation": "qualifies", "hard": False,
             "rule": "duration_unprovable_from_logs",
             "explanation": "Log-retention gaps make the ~3-week duration unprovable on the bundle."},
            {"source": "absence_exposure", "target": "p6_exposed", "relation": "qualifies", "hard": False,
             "rule": "no_corroborating_record",
             "explanation": "No corroborating record — the point is unverified, not a contradiction."},
        ],
    },
    {
        "issue": "CONFORMITY/DEFECT",
        "story": [
            "The contemporaneous Defect Log records the export module overstating revenue.",
            "The forensic expert independently finds a genuine non-conformity.",
            "Conformity is assessed under the Digital Content Directive (EU) 2019/770 — the "
            "defect allegation is supported.",
        ],
        "amendments": [
            "Keep the conformity / defect allegation (P7) — it is evidence-backed (Defect Log + "
            "expert) and squarely within Directive (EU) 2019/770 Art 8.",
        ],
        "claims": [
            {"id": "p7_defect", "kind": "pleading", "prop": "P7",
             "text": "The export module produced materially inaccurate revenue figures (non-conformity)."},
            {"id": "defect_log", "kind": "bundle", "anchor": ("13", 3), "source_type": "defect_log",
             "text": "Defect Log: export module overstates multi-currency revenue by 4-9% (reproduced)."},
            {"id": "expert_defect", "kind": "bundle", "anchor": ("19", 5), "source_type": "expert_report",
             "text": "Forensic expert: the export module is a genuine non-conformity with the spec."},
            {"id": "dcd_overlay", "kind": "legal_overlay", "anchor": ("05", 5), "source_type": "legal_clause",
             "text": "Conformity is assessed under Directive (EU) 2019/770 Art 8 (digital content/services)."},
        ],
        "edges": [
            {"source": "defect_log", "target": "p7_defect", "relation": "supports", "hard": False,
             "rule": "defect_log_supports_nonconformity",
             "explanation": "Contemporaneous Defect Log records the inaccurate-revenue defect."},
            {"source": "expert_defect", "target": "p7_defect", "relation": "supports", "hard": False,
             "rule": "expert_supports_nonconformity",
             "explanation": "The expert independently finds a genuine non-conformity."},
            {"source": "dcd_overlay", "target": "p7_defect", "relation": "supports", "hard": False,
             "rule": "conformity_standard_2019_770",
             "explanation": "Directive (EU) 2019/770 Art 8 supplies the conformity standard."},
        ],
    },
    {
        "issue": "DATA_TRANSFER/SUPERSESSION",
        "story": [
            "P8 is pleaded on the data-transfer standard of Directive 95/46/EC.",
            "The GDPR (Reg (EU) 2016/679, Art 94) repealed that Directive from 25 May 2018.",
            "The parties' 2018 Addendum replaced the standard with the GDPR Chapter V regime.",
            "A claim resting on the superseded instrument cannot stand without re-pleading (P8b).",
        ],
        "amendments": [
            "Re-plead the international-transfer point under GDPR Chapter V and the 2021 standard "
            "contractual clauses, not the repealed Directive 95/46/EC.",
        ],
        "claims": [
            {"id": "p8_transfer", "kind": "pleading", "prop": "P8",
             "text": "Cobalt breached the data-transfer restrictions of Directive 95/46/EC."},
            {"id": "gdpr_repeal", "kind": "legal_overlay", "anchor": ("07", 3), "source_type": "legal_clause",
             "text": "GDPR Art 94 repealed Directive 95/46/EC from 25 May 2018; transfers now under "
                     "GDPR Chapter V (2018 Addendum)."},
        ],
        "edges": [
            {"source": "gdpr_repeal", "target": "p8_transfer", "relation": "supersedes", "hard": True,
             "rule": "later_instrument_supersedes_repealed_directive",
             "explanation": "A claim on the repealed Directive 95/46/EC is superseded by the GDPR; "
                            "it must be re-pleaded under the current law."},
        ],
    },
    {
        "issue": "TRANSFER_MECHANISM/SCHREMS_II",
        "story": [
            "The re-pleadable transfer point (P8b) turns on Chapter V and the current SCCs.",
            "The sub-processor schedule records that SCCs were in place for the US sub-processor.",
            "The 2021 SCC Annex adopted Commission Implementing Decision (EU) 2021/914, replacing "
            "the repealed 2010/87/EU clauses — a second partial supersession.",
            "After Schrems II, SCCs may require supplementary measures; but the bundle contains "
            "no transfer impact assessment or record of such measures.",
            "Unlawfulness is therefore neither established nor excluded — unproven.",
        ],
        "amendments": [
            "If pursuing P8b, plead it under Reg (EU) 2021/914 and Schrems II, and obtain the "
            "transfer impact assessment / supplementary-measures evidence the bundle lacks. "
            "Lawyer review required.",
        ],
        "claims": [
            {"id": "p8b_uschrems", "kind": "pleading", "prop": "P8b",
             "text": "US transfers were unlawful under GDPR Chapter V absent post-Schrems II "
                     "supplementary measures."},
            {"id": "scc_inplace", "kind": "bundle", "anchor": ("25", 3), "source_type": "signed_contract",
             "text": "Sub-processor schedule: transfers to the US sub-processor are made under the "
                     "standard contractual clauses, which are in place."},
            {"id": "scc_module_2021", "kind": "legal_overlay", "anchor": ("11", 2), "source_type": "legal_clause",
             "text": "2021 SCC Annex adopts Commission Implementing Decision (EU) 2021/914, "
                     "replacing the 2010/87/EU clauses (migration by 27 Dec 2022)."},
            {"id": "strand_supplementary", "kind": "bundle", "anchor": ("21", 7), "source_type": "expert_report",
             "text": "Strand: SCCs alone may not suffice post-Schrems II, but she has seen no "
                     "transfer impact assessment or supplementary-measures evidence either way."},
            {"id": "absence_tia", "kind": "absence",
             "text": "No transfer impact assessment or record of supplementary measures appears in "
                     "the bundle."},
        ],
        "edges": [
            {"source": "scc_inplace", "target": "p8b_uschrems", "relation": "attacks", "hard": False,
             "rule": "transfer_mechanism_in_place",
             "explanation": "SCCs were contractually in place — a transfer mechanism existed, "
                            "undercutting a bare 'unlawful transfer' framing."},
            {"source": "scc_module_2021", "target": "p8b_uschrems", "relation": "qualifies", "hard": False,
             "rule": "which_scc_version_applies",
             "explanation": "The applicable SCCs are the 2021/914 clauses (the 2010 clauses being "
                            "superseded) — the point must be framed on the current instrument."},
            {"source": "strand_supplementary", "target": "p8b_uschrems", "relation": "qualifies", "hard": False,
             "rule": "supplementary_measures_open",
             "explanation": "Whether supplementary measures were adequate is genuinely open on the "
                            "evidence."},
            {"source": "absence_tia", "target": "p8b_uschrems", "relation": "qualifies", "hard": False,
             "rule": "absence_of_tia_evidence",
             "explanation": "Absence of the transfer impact assessment leaves the point unproven, "
                            "not contradicted."},
        ],
    },
    {
        "issue": "BACKUPS",
        "story": [
            "The DR runbook records hourly snapshots with 30-day retention and off-region copies.",
            "A 15 July 2025 restore test recovered 99.4% of data within the recovery-time "
            "objective.",
            "'Failed to maintain adequate backups' is contradicted by a documented, tested regime "
            "(GDPR Art 32(1)(c)).",
        ],
        "amendments": [
            "Withdraw the backup-failure allegation: the runbook and a passing restore test "
            "evidence an adequate, tested backup regime.",
        ],
        "claims": [
            {"id": "p9_backups", "kind": "pleading", "prop": "P9",
             "text": "Cobalt failed to maintain adequate backups; data could not be restored."},
            {"id": "restore_test", "kind": "bundle", "anchor": ("31", 3), "source_type": "defect_log",
             "text": "Restore test (15 Jul 2025): recovered 99.4% of the test dataset within the "
                     "four-hour recovery-time objective."},
            {"id": "runbook_exists", "kind": "bundle", "anchor": ("31", 2), "source_type": "defect_log",
             "text": "DR runbook: hourly snapshots, 30-day retention, daily off-region copies."},
        ],
        "edges": [
            {"source": "restore_test", "target": "p9_backups", "relation": "contradicts", "hard": True,
             "rule": "passing_restore_test_contradicts_no_backups",
             "explanation": "A passing restore test contradicts 'failed to maintain adequate "
                            "backups / data could not be restored'."},
            {"source": "runbook_exists", "target": "p9_backups", "relation": "attacks", "hard": False,
             "rule": "documented_backup_regime",
             "explanation": "A documented snapshot/retention regime undercuts the backup-failure "
                            "allegation."},
        ],
    },
    {
        "issue": "PARTIAL_RESTORE",
        "story": [
            "The 15 July restore test left ~0.6% unrecovered — a known legacy-index gap.",
            "Nothing ties that gap to the October breach, and the forensic expert found restore "
            "was not in issue.",
            "Permanent loss in this breach is therefore unproven — it survives but on the "
            "Claimant's burden.",
        ],
        "amendments": [
            "Do not plead permanent data loss from the 0.6% restore gap: it is a legacy-index "
            "issue unrelated to the breach. Obtain breach-specific evidence if pursued.",
        ],
        "claims": [
            {"id": "p9b_lost", "kind": "pleading", "prop": "P9b",
             "text": "A subset of customer data was permanently lost in the breach."},
            {"id": "restore_gap", "kind": "bundle", "anchor": ("31", 4), "source_type": "defect_log",
             "text": "The 0.6% unrecovered relates to a known legacy-index gap, unrelated to any "
                     "specific incident."},
            {"id": "vale_norestore", "kind": "bundle", "anchor": ("19", 8), "source_type": "expert_report",
             "text": "Vale: no evidence that any breached data was unrecoverable; restore was not "
                     "in issue."},
            {"id": "absence_loss", "kind": "absence",
             "text": "No evidence quantifies data permanently lost in the October breach "
                     "specifically."},
        ],
        "edges": [
            {"source": "restore_gap", "target": "p9b_lost", "relation": "qualifies", "hard": False,
             "rule": "legacy_gap_not_breach_loss",
             "explanation": "The 0.6% gap is a legacy-index issue, not breach-caused permanent loss."},
            {"source": "vale_norestore", "target": "p9b_lost", "relation": "attacks", "hard": False,
             "rule": "expert_finds_no_unrecoverable_data",
             "explanation": "The forensic expert found restore was not in issue."},
            {"source": "absence_loss", "target": "p9b_lost", "relation": "qualifies", "hard": False,
             "rule": "no_breach_specific_loss_evidence",
             "explanation": "Absence of breach-specific loss evidence leaves the point unproven."},
        ],
    },
    {
        "issue": "QUANTUM/CAP",
        "story": [
            "Caron (Claimant) accepts ~EUR 900k of subscription fees as wasted expenditure; Roos "
            "(Defendant) would allow only ~EUR 450k — a dispute as to amount, not the head.",
            "Both experts reject the pleaded EUR 6.0m: Caron supports ~EUR 1.1m, Roos ~EUR 0.4m.",
            "A separate ransomware incident and the market explain much of the Q4 downturn.",
            "MSA cl 14 excludes consequential loss and caps liability near fees paid.",
            "GDPR Art 82 compensation is a separate head, apportioned for contributory fault.",
        ],
        "amendments": [
            "Keep the wasted-expenditure claim (P10a) but anticipate the EUR 450k counter-figure. "
            "Reduce / qualify the EUR 6.0m claim (P10b): address both expert figures, the cl.14 "
            "cap, the alternative causation, and apportionment under GDPR Art 82.",
        ],
        "claims": [
            {"id": "p10a_wasted", "kind": "pleading", "prop": "P10a",
             "text": "Wasted subscription fees of EUR 900,000."},
            {"id": "p10b_profit", "kind": "pleading", "prop": "P10b",
             "text": "Loss of profit and Art 82 / regulatory exposure of EUR 6,000,000."},
            {"id": "order_fee", "kind": "bundle", "anchor": ("06", 2), "source_type": "signed_contract",
             "text": "Order Form: annual subscription fee EUR 900,000."},
            {"id": "caron_wasted", "kind": "bundle", "anchor": ("20", 2), "source_type": "expert_report",
             "text": "Caron (Claimant's expert): accepts the ~EUR 900k as wasted expenditure."},
            {"id": "roos_wasted", "kind": "bundle", "anchor": ("22", 2), "source_type": "expert_report",
             "text": "Roos (Defendant's expert): only ~EUR 450k wasted; the Platform delivered "
                     "value for much of the period."},
            {"id": "caron_profit", "kind": "bundle", "anchor": ("20", 4), "source_type": "expert_report",
             "text": "Caron: supportable loss of profit ~EUR 1.1m, not EUR 6.0m."},
            {"id": "roos_profit", "kind": "bundle", "anchor": ("22", 4), "source_type": "expert_report",
             "text": "Roos: recoverable loss of profit no more than ~EUR 0.4m once ransomware and "
                     "market are removed."},
            {"id": "ransomware_market", "kind": "bundle", "anchor": ("20", 6), "source_type": "expert_report",
             "text": "Much of the Q4 downturn is attributable to a separate ransomware incident "
                     "and the market."},
            {"id": "cap_cl14", "kind": "legal_overlay", "anchor": ("03", 14), "source_type": "legal_clause",
             "text": "MSA cl 14 excludes consequential loss and caps liability near fees paid."},
            {"id": "art82_overlay", "kind": "legal_overlay", "anchor": ("04", 14), "source_type": "legal_clause",
             "text": "GDPR Art 82 compensation is a separate statutory head, apportioned by responsibility."},
        ],
        "edges": [
            {"source": "caron_wasted", "target": "p10a_wasted", "relation": "supports", "hard": False,
             "rule": "expert_supports_wasted_expenditure",
             "explanation": "The Claimant's quantum expert supports the ~EUR 900k wasted expenditure."},
            {"source": "order_fee", "target": "p10a_wasted", "relation": "supports", "hard": False,
             "rule": "order_form_evidences_fees",
             "explanation": "The Order Form evidences the EUR 900k of fees paid."},
            {"source": "roos_wasted", "target": "p10a_wasted", "relation": "qualifies", "hard": False,
             "rule": "defendant_expert_lower_wasted_figure",
             "explanation": "The Defendant's expert puts wasted expenditure lower (~EUR 450k) — a "
                            "dispute as to amount, not whether the head is made out."},
            {"source": "cap_cl14", "target": "p10a_wasted", "relation": "caps", "hard": False,
             "rule": "contractual_cap_overlay_wasted",
             "explanation": "cl 14 caps recovery near fees paid — a legal overlay on quantum."},
            {"source": "caron_profit", "target": "p10b_profit", "relation": "contradicts", "hard": True,
             "rule": "numeric_interval_disjoint",
             "explanation": "Pleaded EUR 6.0m is disjoint from Caron's ~EUR 1.1m."},
            {"source": "roos_profit", "target": "p10b_profit", "relation": "contradicts", "hard": True,
             "rule": "numeric_interval_disjoint_defendant",
             "explanation": "Pleaded EUR 6.0m is disjoint from Roos's ~EUR 0.4m — both experts "
                            "reject 6.0m."},
            {"source": "ransomware_market", "target": "p10b_profit", "relation": "qualifies", "hard": False,
             "rule": "alternative_causation",
             "explanation": "A separate ransomware incident and the market are alternative causes."},
            {"source": "cap_cl14", "target": "p10b_profit", "relation": "caps", "hard": False,
             "rule": "contractual_cap_overlay",
             "explanation": "cl 14 caps recovery and excludes consequential loss — a legal overlay."},
            {"source": "art82_overlay", "target": "p10b_profit", "relation": "qualifies", "hard": False,
             "rule": "statutory_apportionment_overlay",
             "explanation": "Art 82 liability is apportioned for the Claimant's contributory fault."},
        ],
    },
    {
        "issue": "ACQUISITION/MERGER",
        "story": [
            "P11 alleges the NorthStar acquisition was implemented without required merger "
            "clearance and used to lock Brightmarket in.",
            "The clearance memorandum records the deal fell below the EU Merger Regulation "
            "(Reg (EC) No 139/2004) thresholds and was in any event notified and cleared.",
            "The interoperability / lock-in complaint is governed by the Data Act and the P2B "
            "Regulation, under which it is not pleaded.",
        ],
        "amendments": [
            "Withdraw the unlawful-acquisition allegation (the deal was cleared); if pursued, "
            "re-plead lock-in under the Data Act (Reg (EU) 2023/2854) switching rules, not merger "
            "control.",
        ],
        "claims": [
            {"id": "p11_merger", "kind": "pleading", "prop": "P11",
             "text": "The NorthStar acquisition was implemented without required EU merger "
                     "clearance and used to lock Brightmarket in."},
            {"id": "sorokin_lockin", "kind": "bundle", "anchor": ("18", 3), "source_type": "witness_statement",
             "text": "Brightmarket programme lead: after the acquisition export became harder — "
                     "perceived lock-in."},
            {"id": "clearance_doc", "kind": "bundle", "anchor": ("15", 2), "source_type": "legal_clause",
             "text": "Clearance memorandum: the deal fell below the EU Merger Regulation thresholds "
                     "and was notified and cleared."},
            {"id": "eumr_overlay", "kind": "legal_overlay", "anchor": ("15", 4), "source_type": "legal_clause",
             "text": "Council Regulation (EC) No 139/2004 (EU Merger Regulation): thresholds / "
                     "notification regime."},
            {"id": "dataact_overlay", "kind": "legal_overlay", "anchor": ("04", 12), "source_type": "legal_clause",
             "text": "Switching / interoperability is governed by the Data Act (Reg (EU) 2023/2854) "
                     "and DPA cl 12."},
        ],
        "edges": [
            {"source": "clearance_doc", "target": "p11_merger", "relation": "contradicts", "hard": True,
             "rule": "cleared_acquisition_contradicts_unlawful",
             "explanation": "A notified-and-cleared, below-threshold deal contradicts 'implemented "
                            "without required clearance'."},
            {"source": "eumr_overlay", "target": "p11_merger", "relation": "legal_bar", "hard": False,
             "rule": "merger_regulation_overlay",
             "explanation": "The EU Merger Regulation regime bars the unlawful-acquisition framing."},
            {"source": "dataact_overlay", "target": "p11_merger", "relation": "qualifies", "hard": False,
             "rule": "wrong_legal_basis_lockin",
             "explanation": "Lock-in / interoperability belongs under the Data Act and P2B Regulation, "
                            "not merger control."},
            {"source": "sorokin_lockin", "target": "p11_merger", "relation": "supports", "hard": False,
             "rule": "witness_perceived_lockin",
             "explanation": "The programme lead perceived lock-in (untested, and not the pleaded "
                            "merger-control basis)."},
        ],
    },
    {
        "issue": "AUTOMATED_DECISIONS/AI_ACT",
        "story": [
            "P12 alleges the forecasting system made automated decisions affecting customers "
            "without the safeguards required by GDPR Art 22 and the AI Act.",
            "No document evidences any solely-automated decision producing legal or similarly "
            "significant effects on a data subject; the only support is hearsay.",
            "The DPIA records the model as a B2B analytics aid, not an Annex III high-risk AI "
            "system, and the AI Act's high-risk obligations were not yet in application.",
            "An evidence gap overlaid with a temporal-scope problem.",
        ],
        "amendments": [
            "Do not plead an Art 22 / AI Act case without evidence of a solely-automated decision "
            "with legal or significant effect; note the AI Act high-risk obligations were not yet "
            "in application. Lawyer review required.",
        ],
        "claims": [
            {"id": "p12_ai", "kind": "pleading", "prop": "P12",
             "text": "Cobalt's forecasting system made automated decisions affecting customers "
                     "without the required safeguards (GDPR Art 22; AI Act)."},
            {"id": "ds_hearsay_ai", "kind": "bundle", "anchor": ("18", 4), "source_type": "witness_statement",
             "text": "Programme lead: 'I understand the forecasting model was used to make "
                     "automated decisions about customers' — second-hand, not witnessed."},
            {"id": "dpia_not_highrisk", "kind": "legal_overlay", "anchor": ("14", 6), "source_type": "legal_clause",
             "text": "DPIA: the model is a B2B analytics aid, not a solely-automated decision nor "
                     "an Annex III high-risk AI system; AI Act high-risk duties not yet in force."},
            {"id": "absence_art22", "kind": "absence",
             "text": "No document evidences a solely-automated decision with legal or similarly "
                     "significant effect on a data subject (GDPR Art 22)."},
        ],
        "edges": [
            {"source": "ds_hearsay_ai", "target": "p12_ai", "relation": "qualifies", "hard": False,
             "rule": "hearsay_belief_only",
             "explanation": "The only support is a second-hand belief — hearsay, no personal "
                            "knowledge."},
            {"source": "dpia_not_highrisk", "target": "p12_ai", "relation": "qualifies", "hard": False,
             "rule": "not_highrisk_not_yet_in_force",
             "explanation": "The model is not an Annex III high-risk system and the AI Act "
                            "high-risk duties were not yet in application — a temporal-scope point."},
            {"source": "absence_art22", "target": "p12_ai", "relation": "qualifies", "hard": False,
             "rule": "no_automated_decision_evidence",
             "explanation": "No evidence of a qualifying automated decision — an evidence gap."},
        ],
    },
    {
        "issue": "EPRIVACY/COOKIES",
        "story": [
            "P13 alleges Cobalt set non-essential cookies without the consent required by "
            "ePrivacy Art 5(3).",
            "The consent-configuration log shows a banner WAS deployed but that, in a sample, "
            "some analytics cookies fired before consent.",
            "The log does not attribute those cookies to Cobalt rather than Brightmarket's own "
            "tag manager; the only other support is hearsay.",
            "Consent is engaged, but breach by Cobalt is unproven.",
        ],
        "amendments": [
            "Do not plead the cookie/ePrivacy breach against Cobalt without attribution evidence: "
            "the log does not show the offending cookies were Cobalt's rather than the Customer's "
            "own tag manager. Lawyer review required.",
        ],
        "claims": [
            {"id": "p13_cookies", "kind": "pleading", "prop": "P13",
             "text": "Cobalt set non-essential cookies without valid consent (ePrivacy Art 5(3))."},
            {"id": "consent_log", "kind": "bundle", "anchor": ("32", 3), "source_type": "defect_log",
             "text": "Consent log: a banner was active, but in a sample some analytics cookies "
                     "fired before consent — owner not attributed."},
            {"id": "sorokin_cookie_hearsay", "kind": "bundle", "anchor": ("18", 5), "source_type": "witness_statement",
             "text": "Programme lead: 'I am told by our marketing team' that Cobalt set tracking "
                     "cookies without consent — second-hand, not reviewed."},
            {"id": "eprivacy_overlay", "kind": "legal_overlay", "anchor": ("05", 7), "source_type": "legal_clause",
             "text": "SOW cl.7 / ePrivacy Art 5(3): cookies require consent; the Customer operates "
                     "its own consent-management and tag manager."},
            {"id": "absence_attribution", "kind": "absence",
             "text": "No evidence attributes the non-consented cookies to Cobalt rather than the "
                     "Customer's own tag manager."},
        ],
        "edges": [
            {"source": "consent_log", "target": "p13_cookies", "relation": "qualifies", "hard": False,
             "rule": "ambiguous_consent_sample",
             "explanation": "The log shows some pre-consent cookies but does not establish breach "
                            "or attribution."},
            {"source": "sorokin_cookie_hearsay", "target": "p13_cookies", "relation": "qualifies", "hard": False,
             "rule": "hearsay_marketing_belief",
             "explanation": "Second-hand marketing belief — hearsay, no personal knowledge."},
            {"source": "eprivacy_overlay", "target": "p13_cookies", "relation": "qualifies", "hard": False,
             "rule": "consent_standard_and_customer_tagmanager",
             "explanation": "Art 5(3) supplies the consent standard, but the Customer runs its own "
                            "tag manager — attribution is in issue."},
            {"source": "absence_attribution", "target": "p13_cookies", "relation": "qualifies", "hard": False,
             "rule": "no_attribution_evidence",
             "explanation": "No attribution evidence — the point is unverified, not contradicted."},
        ],
    },
    {
        "issue": "DSAR/ERASURE",
        "story": [
            "P14 alleges Cobalt failed to assist with, and itself failed to action, data-subject "
            "access and erasure requests.",
            "The DSAR/erasure register records 412 requests, all closed within statutory time, "
            "with no request refused or unactioned by the processor.",
            "No document identifies a single request Cobalt failed to action — the allegation is "
            "unparticularised.",
            "Absence of evidence of a failure is an evidence gap, not proof of one.",
        ],
        "amendments": [
            "Do not plead the DSAR/erasure failure without identifying a specific request and a "
            "specific failure; the register shows requests closed in time. Lawyer review required.",
        ],
        "claims": [
            {"id": "p14_dsar", "kind": "pleading", "prop": "P14",
             "text": "Cobalt failed to assist with and action data-subject access / erasure "
                     "requests (GDPR Arts 12, 15, 17)."},
            {"id": "dsar_register", "kind": "bundle", "anchor": ("33", 3), "source_type": "defect_log",
             "text": "DSAR/erasure register: 412 requests, all closed within statutory time; none "
                     "recorded as refused or unactioned by the processor."},
            {"id": "dsar_assist_overlay", "kind": "legal_overlay", "anchor": ("04", 6), "source_type": "legal_clause",
             "text": "DPA cl.6 / GDPR Arts 12-23: the processor must assist the controller in "
                     "responding to access and erasure requests."},
            {"id": "absence_dsar", "kind": "absence",
             "text": "No document identifies a specific access or erasure request that Cobalt "
                     "failed to action."},
        ],
        "edges": [
            {"source": "dsar_register", "target": "p14_dsar", "relation": "qualifies", "hard": False,
             "rule": "register_shows_no_failure",
             "explanation": "The register shows requests closed in time and none unactioned — the "
                            "allegation is unparticularised."},
            {"source": "dsar_assist_overlay", "target": "p14_dsar", "relation": "qualifies", "hard": False,
             "rule": "assistance_duty_standard",
             "explanation": "The assistance duty supplies the standard, but no specific failure is "
                            "identified."},
            {"source": "absence_dsar", "target": "p14_dsar", "relation": "qualifies", "hard": False,
             "rule": "no_identified_failure",
             "explanation": "Absence of any identified failure is an evidence gap, not a breach."},
        ],
    },
]


# Claims whose support is hearsay (relayed, no personal knowledge) — drives the
# per-claim admissibility overlay the frontend expects.
HEARSAY_CLAIMS: set[str] = {"dpo_hearsay", "ds_hearsay_ai", "sorokin_cookie_hearsay"}


# ---------------------------------------------------------------- chronology
# [{n, date, event, evidence:[{tab,para}], remarks, source}] — source "counsel"
# (pleaded / agreed) or "ai" (engine-surfaced). Mirrors the frontend contract.
CHRONOLOGY: list[dict] = [
    {"n": 1, "date": "2016-12-05",
     "event": "Pre-contract sales email describes the Platform as 'ISO 27001 certified and GDPR-compliant by design'.",
     "evidence": [{"tab": "30", "para": 2}],
     "remarks": "The representation underlying P1 was made — but see the audit scope (doc 27).", "source": "ai"},
    {"n": 2, "date": "2016-12-20",
     "event": "Brightmarket's own procurement note records it verified and relied on Cobalt's ISO 27001 certificate.",
     "evidence": [{"tab": "34", "para": 3}],
     "remarks": "Own-goal cutting against 'the representation was false' (P1).", "source": "ai"},
    {"n": 3, "date": "2017-03-01",
     "event": "Parties enter the MSA, DPA and SOW; Cobalt appointed as Brightmarket's processor.",
     "evidence": [{"tab": "03", "para": 1}, {"tab": "04", "para": 1}],
     "remarks": "", "source": "counsel"},
    {"n": 4, "date": "2018-05-20",
     "event": "GDPR Addendum: references to Directive 95/46/EC replaced with the GDPR Chapter V regime.",
     "evidence": [{"tab": "07", "para": 3}],
     "remarks": "Supersedes the data-transfer standard pleaded in P8.", "source": "ai"},
    {"n": 5, "date": "2021-11-30",
     "event": "International Transfer Annex adopts the 2021 SCCs (Dec (EU) 2021/914), replacing the 2010/87/EU clauses.",
     "evidence": [{"tab": "11", "para": 2}],
     "remarks": "Second partial supersession; bears on the transfer mechanism (P8b).", "source": "ai"},
    {"n": 6, "date": "2024-09-12",
     "event": "Cobalt's acquisition of NorthStar notified and cleared; below EU Merger Regulation thresholds.",
     "evidence": [{"tab": "15", "para": 2}, {"tab": "15", "para": 4}],
     "remarks": "Contradicts P11 (acquisition 'without required clearance').", "source": "ai"},
    {"n": 7, "date": "2025-02-18",
     "event": "Internal Cobalt email: merchant datasets used to train a forecasting model without consent.",
     "evidence": [{"tab": "10", "para": 2}],
     "remarks": "Admission underpinning P2 (contested by the CTO, doc 28).", "source": "ai"},
    {"n": 8, "date": "2025-06-03",
     "event": "Cobalt issues written security-hardening guidance: enable administrator MFA.",
     "evidence": [{"tab": "09", "para": 2}],
     "remarks": "", "source": "counsel"},
    {"n": 9, "date": "2025-07-15",
     "event": "DR restore test recovers 99.4% of data within the recovery-time objective.",
     "evidence": [{"tab": "31", "para": 3}],
     "remarks": "Contradicts P9 (no adequate backups); the 0.6% gap underlies P9b.", "source": "ai"},
    {"n": 10, "date": "2025-08-08",
     "event": "Penetration test finds a publicly reachable staging endpoint — production exposure unconfirmed.",
     "evidence": [{"tab": "26", "para": 4}],
     "remarks": "Ambiguous support for P6 (public exposure).", "source": "ai"},
    {"n": 11, "date": "2025-09-20",
     "event": "Defect Log records the export module overstating multi-currency revenue.",
     "evidence": [{"tab": "13", "para": 3}],
     "remarks": "Supports P7 (conformity).", "source": "counsel"},
    {"n": 12, "date": "2025-10-10",
     "event": "Personal-data breach detected.",
     "evidence": [{"tab": "02", "para": 9}],
     "remarks": "", "source": "counsel"},
    {"n": 13, "date": "2025-10-11",
     "event": "Cobalt notifies Brightmarket of the breach within 18 hours.",
     "evidence": [{"tab": "08", "para": 1}, {"tab": "08", "para": 2}],
     "remarks": "Processor's Art 33(2) duty discharged; supervisory-authority notice was the "
                "controller's (P4 allocation trap).", "source": "ai"},
    {"n": 14, "date": "2025-10-16",
     "event": "Brightmarket (controller) notifies the DPC — on day 6, late — putting affected data subjects at ~19,000.",
     "evidence": [{"tab": "24", "para": 2}, {"tab": "24", "para": 3}],
     "remarks": "Own-goal: contradicts P3 (2.3m) and shows the 72h duty was the controller's (P4).", "source": "ai"},
    {"n": 15, "date": "2025-11-05",
     "event": "Brightmarket's own internal security review finds its admins had disabled MFA.",
     "evidence": [{"tab": "12", "para": 4}],
     "remarks": "Own-goal undermining P5 (sole cause).", "source": "ai"},
    {"n": 16, "date": "2025-12-02",
     "event": "DPC letter: notification was late; the processor had informed the controller without undue delay.",
     "evidence": [{"tab": "23", "para": 2}],
     "remarks": "Reinforces the P4 allocation trap; controller/processor assessment ongoing.", "source": "ai"},
    {"n": 17, "date": "2026-02-10",
     "event": "Brightmarket issues proceedings (Particulars of Claim).",
     "evidence": [{"tab": "02", "para": 7}],
     "remarks": "", "source": "counsel"},
    {"n": 18, "date": "2026-04-30",
     "event": "Joint forensic expert (Vale): ~14,000 records exfiltrated, not 2.3 million.",
     "evidence": [{"tab": "19", "para": 3}],
     "remarks": "Contradicts P3; conflicts with the DPO's witness estimate.", "source": "ai"},
    {"n": 19, "date": "2026-05-12",
     "event": "Claimant's expert (Strand) agrees ~14,000 exfiltrated but argues ~1.9m 'exposed' and a Cobalt segmentation failing.",
     "evidence": [{"tab": "21", "para": 4}, {"tab": "21", "para": 6}],
     "remarks": "Dueling experts: drives the murk in P3b (exposure) and P5 (concurrent causation).", "source": "ai"},
]
