"""Deliberately TREACHEROUS extension of the EU case (*Brightmarket Retail GmbH v
Cobalt Cloud Analytics Ltd*, GDPR) — planted traps with ENGINE-AGNOSTIC ground truth.

Where ``data/eu_case_gold.py`` is a *murky* case (genuinely unclear points), this
module plants seven *adversarial* allegations whose pleaded framing is superficially
plausible but is defeated, qualified, or left genuinely open by the bundle. Each trap
is designed so a careless engine (or a careless lawyer) would mark it SUPPORTED, while
the controlling evidence in fact CONTRADICTS it or forces a VERIFY/UNVERIFIED outcome.

The truth here is **engine-agnostic**: ``TRAP_GOLD`` records, per pleaded proposition,
the correct verdict, the legal-risk overlay, the confidence band, whether a human must
verify, the OPERATIVE evidence (the document that actually controls), the DECOY evidence
(the document that superficially supports the pleading), and a ``must_not`` list of
verdicts an engine may never return. ``tests/test_eu_traps.py`` proves the analysis
engine catches OR correctly verify-flags every trap and NEVER marks a planted-unsupported
claim as SUPPORTED at high confidence.

The seven traps (P15..P21), pleaded at Particulars of Claim ¶24..¶30:
  * P15  SEMANTIC NEAR-MISS    — an SLA "target" mis-pleaded as an uptime *warranty*.
  * P16  NUMERIC / UNIT        — 30 hours mis-stated as 30 days; gross revenue as margin.
  * P17  DATE / CHRONOLOGY      — a 25 *October* post-breach email mis-pleaded as a
                                  25 *September* pre-breach warning that was "ignored".
  * P18  MULTI-DOC INFERENCE    — a broken India-transfer chain (de-listed sub-processor,
                                  synthetic-only sandbox, EU engineer on a Mumbai VPN).
  * P19  NEAR-DUPLICATE         — an *uncapped* indemnity drawn from a superseded DRAFT;
                                  the EXECUTED DPA caps it and supersedes the draft.
  * P20  GENUINELY AMBIGUOUS    — a legacy 3DES tier; the expert declines to opine.
  * P21  ALLOCATION + OWN-GOAL  — the Art 35 DPIA was the *controller's* duty, and
                                  Brightmarket itself authored the DPIA (doc 14).

Every drafted paragraph is verbatim-anchorable; every cited quote in ``QUOTES`` is an
exact substring of the paragraph it cites. New documents are tabs "35".."46"; the trap
pleadings extend the Particulars of Claim (doc "02") at ¶24..¶30.

**Draft — legal review pending.**
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data import eu_case_gold as EUG  # noqa: E402


# --------------------------------------------------------------- the trap types
# Item (j) of the harness asserts all seven are present and distinct.
TRAP_TYPES: tuple[str, ...] = (
    "semantic_near_miss",
    "numeric_unit",
    "date_chronology",
    "multi_doc_inference",
    "near_duplicate_supersession",
    "genuinely_ambiguous",
    "allocation_burden_own_goal",
)


# ---------------------------------------------------------------- new documents
# id -> {title, doc_type, party, date, category, modality, paras:[(n, verbatim text)]}.
# ``doc_type`` uses the legacy coarse enum (contract/record/correspondence/expert);
# ``category`` / ``modality`` use the richer frontend vocabularies.
TRAP_DOCS: dict[str, dict] = {
    "35": {
        "title": "Service Level Annex (availability target)",
        "doc_type": "contract", "party": "neutral", "date": "2017-03-01",
        "category": "Contract", "modality": "document",
        "paras": [
            (1, "Service Level Annex to the Master Subscription Agreement, between "
                "Brightmarket Retail GmbH and Cobalt Cloud Analytics Ltd."),
            (2, "The Platform has a monthly availability target of 99.9%."),
            (3, "This figure is a service-level target only and is not a warranty or "
                "guarantee of uptime; the Customer's sole and exclusive remedy for any "
                "failure to meet the target is the service credits set out in paragraph 4, "
                "and the Supplier shall have no liability in damages for unavailability."),
            (4, "Service credits are capped at 10% of the monthly fee for the affected "
                "month and are the only compensation payable for a missed availability target."),
        ],
    },
    "36": {
        "title": "Outage Impact Assessment (October 2025)",
        "doc_type": "record", "party": "neutral", "date": "2025-10-12",
        "category": "Record", "modality": "document",
        "paras": [
            (1, "Outage Impact Assessment — Brightmarket / Cobalt analytics dashboard "
                "incident, October 2025."),
            (2, "The outage lasted approximately 30 hours, from 02:00 on 10 October 2025 "
                "to 08:00 on 11 October 2025."),
            (3, "Brightmarket's average daily gross revenue across the affected stores is "
                "approximately EUR 150,000; this figure is gross revenue, not margin."),
            (4, "The public storefront remained available throughout; only the internal "
                "analytics dashboard was affected, and the estimated gross-margin impact of "
                "the outage is approximately EUR 30,000."),
        ],
    },
    "37": {
        "title": "Email — post-breach follow-up (Brightmarket to Cobalt)",
        "doc_type": "correspondence", "party": "claimant", "date": "2025-10-25",
        "category": "Correspondence", "modality": "email",
        "paras": [
            (1, "From: Brightmarket IT. To: Cobalt Support. Sent: 25 October 2025, 14:10. "
                "Subject: Follow-up after the 10 October breach."),
            (2, "Following the breach earlier this month, please review the security-group "
                "configuration; treat this email as a formal warning that any recurrence "
                "will be escalated."),
        ],
    },
    "38": {
        "title": "Remediation Ticket Register (extract)",
        "doc_type": "record", "party": "neutral", "date": "2025-10-12",
        "category": "Record", "modality": "document",
        "paras": [
            (1, "Remediation Ticket Register (extract) — Cobalt platform operations."),
            (2, "Ticket SEC-1187 was opened at 09:00 on 12 October 2025 and closed at 17:40 "
                "on 12 October 2025; the misconfiguration was remediated the same day."),
        ],
    },
    "39": {
        "title": "Sub-processor Register (extract)",
        "doc_type": "contract", "party": "neutral", "date": "2024-04-15",
        "category": "Contract", "modality": "document",
        "paras": [
            (1, "Sub-processor Register (extract) — Cobalt Cloud Analytics Ltd."),
            (2, "The India-based sub-processor, Cobalt Analytics India Pvt Ltd, was de-listed "
                "and removed from the sub-processor register on 30 November 2023; no "
                "production personal data has been routed to it since."),
        ],
    },
    "40": {
        "title": "Data-Flow Map (extract)",
        "doc_type": "record", "party": "neutral", "date": "2025-09-01",
        "category": "Record", "modality": "document",
        "paras": [
            (1, "Data-Flow Map (extract) — Brightmarket processing environments."),
            (2, "The India development sandbox processes synthetic and de-identified test "
                "data only; no EU customer personal data flows to the India environment."),
        ],
    },
    "41": {
        "title": "Access Log (extract) — analytics tier",
        "doc_type": "record", "party": "neutral", "date": "2025-10-12",
        "category": "Record", "modality": "document",
        "paras": [
            (1, "Access Log (extract): an inbound session from a Mumbai (India) IP address, "
                "203.0.113.7, reached the analytics tier on 12 October 2025."),
            (2, "On investigation, that session resolves to an EU-based engineer connecting "
                "through the company's Mumbai VPN egress node; the underlying access "
                "originated from within the EU."),
        ],
    },
    "42": {
        "title": "Data Processing Agreement — DRAFT v0.9 (subject to contract)",
        "doc_type": "contract", "party": "neutral", "date": "2017-02-01",
        "category": "Amendment", "modality": "document",
        "paras": [
            (1, "Data Processing Agreement — DRAFT v0.9. Marked 'subject to contract'; not "
                "executed."),
            (7, "Indemnity (draft): the Supplier shall indemnify the Customer without limit "
                "for any data-protection breach."),
        ],
    },
    "43": {
        "title": "Data Processing Agreement — EXECUTED (indemnity clause 11)",
        "doc_type": "contract", "party": "neutral", "date": "2017-03-01",
        "category": "Contract", "modality": "document",
        "paras": [
            (1, "Data Processing Agreement — EXECUTED version, signed 1 March 2017."),
            (11, "Indemnity: the Supplier's indemnity for data-protection breaches is capped "
                 "at the fees paid in the preceding 12 months; this executed Agreement "
                 "supersedes any prior draft, including draft v0.9."),
        ],
    },
    "44": {
        "title": "Encryption Configuration Note",
        "doc_type": "record", "party": "neutral", "date": "2025-09-01",
        "category": "Record", "modality": "document",
        "paras": [
            (1, "Encryption Configuration Note — Brightmarket / Cobalt platform."),
            (2, "Customer data at rest is encrypted with AES-256."),
            (3, "A legacy archive tier still uses 3DES; migration of that tier to AES-256 is "
                "scheduled for Q4 2025."),
        ],
    },
    "45": {
        "title": "Expert Addendum — Dr Vale (encryption sufficiency)",
        "doc_type": "expert", "party": "neutral", "date": "2026-05-12",
        "category": "Witness (expert)", "modality": "document",
        "paras": [
            (1, "Expert Addendum — Dr Idris Vale, on encryption sufficiency."),
            (2, "I am unable to opine whether retaining 3DES on the legacy archive tier fell "
                "below the Article 32 standard; reasonable security experts may differ, and "
                "the answer turns on the residual risk of that specific tier."),
        ],
    },
    "46": {
        "title": "Data Processing Agreement — clause 10 (DPIA allocation)",
        "doc_type": "contract", "party": "neutral", "date": "2017-03-01",
        "category": "Contract", "modality": "document",
        "paras": [
            (1, "Data Processing Agreement — clause 10 (assessments and assistance)."),
            (2, "The Controller is responsible for carrying out any data protection impact "
                "assessment required by Article 35 GDPR; the Processor shall provide "
                "reasonable assistance under Article 28(3)(f)."),
        ],
    },
}


# --------------------------------------------- trap pleadings (extend doc "02")
# Verbatim Particulars-of-Claim paragraphs at ¶24..¶30. Each trap proposition is
# pleaded here; the Pleading view annotates ``documents["02"]``.
TRAP_PLEADED_PARAS: dict[int, str] = {
    24: "The Defendant warranted that the Platform would achieve 99.9% uptime, and is "
        "liable in damages for failing to meet that uptime warranty.",
    25: "The October 2025 outage lasted 30 days and, at EUR 150,000 of lost margin per "
        "day, caused the Claimant EUR 4,500,000 in lost profit.",
    26: "On 25 September 2025, before the breach, the Claimant warned the Defendant of the "
        "vulnerability, and the Defendant ignored that warning and failed to remediate it.",
    27: "The Defendant unlawfully transferred the personal data of EU customers to its "
        "sub-processor in India in October 2025.",
    28: "Under the Data Processing Agreement the Defendant gave an unlimited, uncapped "
        "indemnity for any data-protection breach.",
    29: "The Defendant's encryption fell below the standard required by Article 32 GDPR "
        "because it used a deprecated cipher.",
    30: "The Defendant failed to carry out the data protection impact assessment required "
        "by Article 35 GDPR.",
}


# ------------------------------------------------------------- trap propositions
TRAP_PROPOSITIONS: list[dict] = [
    {"id": "P15", "pleaded_at": ("02", 24),
     "text": "Cobalt warranted that the Platform would achieve 99.9% uptime and is liable "
             "in damages for failing to meet that uptime warranty."},
    {"id": "P16", "pleaded_at": ("02", 25),
     "text": "The October 2025 outage lasted 30 days and caused the Claimant EUR 4,500,000 "
             "in lost profit, at EUR 150,000 of lost margin per day."},
    {"id": "P17", "pleaded_at": ("02", 26),
     "text": "On 25 September 2025, before the breach, Brightmarket warned Cobalt of the "
             "vulnerability and Cobalt ignored the warning and failed to remediate."},
    {"id": "P18", "pleaded_at": ("02", 27),
     "text": "Cobalt unlawfully transferred EU customers' personal data to its "
             "sub-processor in India."},
    {"id": "P19", "pleaded_at": ("02", 28),
     "text": "Under the Data Processing Agreement Cobalt gave an unlimited, uncapped "
             "indemnity for data-protection breaches."},
    {"id": "P20", "pleaded_at": ("02", 29),
     "text": "Cobalt's encryption fell below the Article 32 GDPR standard because it used a "
             "deprecated cipher."},
    {"id": "P21", "pleaded_at": ("02", 30),
     "text": "Cobalt failed to carry out the data protection impact assessment required by "
             "Article 35 GDPR."},
]


# ------------------------------------------------------------------- the oracle
# Per trap: trap_type, verdict, legal_risk (overlay), confidence_band, verify,
# must_not, operative_evidence (the controlling document), decoy_evidence (the
# superficially-supportive document), rationale, acts, issue, amendment, own_goal,
# and (P16) the numeric pair the deterministic solver proves disjoint.
#
# legal_risk vocabulary: NONE | CONTRACTUALLY_BARRED | SUPERSEDED | CAPPED |
# CAUSATION_PROBLEM | BURDEN_PROBLEM | TEMPORAL_SCOPE.
TRAP_GOLD: dict[str, dict] = {
    "P15": {
        "trap_type": "semantic_near_miss",
        "issue": "SLA/WARRANTY",
        "verdict": "CONTRADICTED", "legal_risk": "CONTRACTUALLY_BARRED",
        "confidence_band": "high", "verify": False,
        "must_not": ["SUPPORTED"],
        "operative_evidence": [("35", 3)],
        "decoy_evidence": [("35", 2)],
        "acts": [],
        "own_goal": False,
        "rationale": "Semantic near-miss. The SLA's 99.9% is expressly 'a service-level "
                     "target only and is not a warranty or guarantee of uptime' (35¶3); the "
                     "sole remedy is service credits and the Supplier has 'no liability in "
                     "damages for unavailability'. Pleading it as an uptime WARRANTY with "
                     "damages is contradicted by, and contractually barred by, the very "
                     "clause relied on. The 99.9% figure (35¶2) is a decoy.",
        "amendment": "Withdraw the uptime-warranty claim: the SLA states the figure is a "
                     "target, not a warranty, with service credits as the sole remedy.",
    },
    "P16": {
        "trap_type": "numeric_unit",
        "issue": "OUTAGE/QUANTUM",
        "verdict": "CONTRADICTED", "legal_risk": "CAUSATION_PROBLEM",
        "confidence_band": "high", "verify": False,
        "must_not": ["SUPPORTED"],
        "operative_evidence": [("36", 2), ("36", 4)],
        "decoy_evidence": [("36", 3)],
        "acts": [],
        "own_goal": False,
        "numeric": [{
            "label": "outage_lost_profit",
            "entity": "Brightmarket October 2025 outage",
            "metric": "lost profit attributable to the outage",
            "pleaded": 4_500_000.0, "evidence": 30_000.0,
            "pleaded_anchor": ("02", 25), "evidence_anchor": ("36", 4),
            "tolerance": 100_000.0, "unit": "EUR",
        }],
        "rationale": "Numeric / unit trap. The outage lasted ~30 HOURS not 30 days (36¶2), "
                     "the storefront stayed up, and the gross-margin impact was ~EUR 30,000 "
                     "(36¶4). The pleaded EUR 4,500,000 multiplies a 30-day duration by EUR "
                     "150,000 of DAILY GROSS REVENUE (a decoy figure expressly 'gross "
                     "revenue, not margin', 36¶3). The deterministic solver proves EUR 4.5m "
                     "and EUR 30k are disjoint.",
        "amendment": "Re-plead quantum on the ~30-hour duration and the ~EUR 30k margin "
                     "impact; do not multiply a 30-day window by daily gross revenue.",
    },
    "P17": {
        "trap_type": "date_chronology",
        "issue": "WARNING/CHRONOLOGY",
        "verdict": "CONTRADICTED", "legal_risk": "BURDEN_PROBLEM",
        "confidence_band": "high", "verify": False,
        "must_not": ["SUPPORTED"],
        "operative_evidence": [("37", 1), ("38", 2)],
        "decoy_evidence": [("37", 2)],
        "acts": [],
        "own_goal": False,
        "rationale": "Date / chronology trap. The only 'warning' email is dated 25 OCTOBER "
                     "2025 — a post-breach follow-up (37¶1) — not a 25 September pre-breach "
                     "warning, and the misconfiguration was in fact remediated the SAME DAY "
                     "it was ticketed, 12 October (38¶2). The pleaded 'ignored a 25 "
                     "September warning and failed to remediate' is contradicted on both "
                     "the date and the remediation. The 'formal warning' wording (37¶2) is "
                     "a decoy.",
        "amendment": "Withdraw the pre-breach-warning allegation: the email post-dates the "
                     "breach (25 October) and the fix was completed the same day it was "
                     "raised.",
    },
    "P18": {
        "trap_type": "multi_doc_inference",
        "issue": "TRANSFER/INDIA",
        "verdict": "CONTRADICTED", "legal_risk": "NONE",
        "confidence_band": "medium", "verify": True,
        "must_not": ["SUPPORTED"],
        "operative_evidence": [("39", 2), ("40", 2), ("41", 2)],
        "decoy_evidence": [("41", 1)],
        "acts": ["32016R0679"],
        "own_goal": False,
        "rationale": "Multi-document inference with a broken chain. The India sub-processor "
                     "was DE-LISTED on 30 November 2023 (39¶2); the India sandbox handles "
                     "SYNTHETIC, de-identified data only (40¶2); and the single India IP in "
                     "the window resolves to an EU engineer on a Mumbai VPN egress node "
                     "(41¶2). No EU personal data was transferred to India. The raw 'India "
                     "IP' log line (41¶1) is the decoy. Because the inference spans three "
                     "documents, a human should verify the chain.",
        "amendment": "Drop the India-transfer allegation unless contrary primary evidence "
                     "exists; the register, data-flow map and access log each break the "
                     "pleaded chain.",
    },
    "P19": {
        "trap_type": "near_duplicate_supersession",
        "issue": "INDEMNITY/SUPERSESSION",
        "verdict": "CONTRADICTED", "legal_risk": "SUPERSEDED",
        "confidence_band": "high", "verify": False,
        "must_not": ["SUPPORTED"],
        "operative_evidence": [("43", 11)],
        "decoy_evidence": [("42", 7)],
        "acts": [],
        "own_goal": False,
        "rationale": "Near-duplicate / supersession trap. The 'unlimited' indemnity appears "
                     "only in an unexecuted DRAFT v0.9 marked 'subject to contract' (42¶7). "
                     "The EXECUTED DPA caps the indemnity at 12 months' fees and expressly "
                     "'supersedes any prior draft, including draft v0.9' (43¶11). Pleading "
                     "the uncapped draft figure is contradicted by, and superseded by, the "
                     "signed agreement. The draft clause (42¶7) is the decoy.",
        "amendment": "Plead the indemnity from the EXECUTED DPA (capped at 12 months' "
                     "fees), not the superseded draft v0.9.",
    },
    "P20": {
        "trap_type": "genuinely_ambiguous",
        "issue": "ENCRYPTION/ART32",
        "verdict": "UNVERIFIED", "legal_risk": "BURDEN_PROBLEM",
        "confidence_band": "low", "verify": True,
        "must_not": ["SUPPORTED", "CONTRADICTED"],
        "operative_evidence": [("44", 3), ("45", 2)],
        "decoy_evidence": [("44", 2)],
        "acts": ["32016R0679"],
        "own_goal": False,
        "rationale": "Genuinely ambiguous. Primary data at rest uses AES-256 (44¶2, a "
                     "defence decoy), but a legacy archive tier still uses 3DES with "
                     "migration scheduled for Q4 2025 (44¶3). The expert expressly DECLINES "
                     "to opine whether retaining 3DES fell below Article 32, noting "
                     "reasonable experts may differ (45¶2). Neither 'below standard' nor "
                     "'compliant' is made out — the burden is the Claimant's, so the point "
                     "is UNVERIFIED and a human must decide.",
        "amendment": "Do not assert an Article 32 breach on the legacy 3DES tier without "
                     "expert opinion on its residual risk; obtain a substantive opinion.",
    },
    "P21": {
        "trap_type": "allocation_burden_own_goal",
        "issue": "DPIA/ALLOCATION",
        "verdict": "CONTRADICTED", "legal_risk": "CONTRACTUALLY_BARRED",
        "confidence_band": "high", "verify": False,
        "must_not": ["SUPPORTED"],
        "operative_evidence": [("46", 2), ("14", 1)],
        "decoy_evidence": [],
        "acts": ["32016R0679"],
        "own_goal": True,
        "rationale": "Allocation trap with an own-goal. DPA clause 10 allocates the Article "
                     "35 DPIA to the CONTROLLER, the Processor only providing reasonable "
                     "assistance under Article 28(3)(f) (46¶2). And Brightmarket itself "
                     "authored the DPIA (doc 14¶1) — so the duty pleaded against Cobalt was "
                     "the Claimant's own, and it was in fact carried out. CONTRADICTED and "
                     "contractually barred.",
        "amendment": "Withdraw the DPIA-failure allegation: the Art 35 DPIA was the "
                     "controller's duty (DPA cl 10) and Brightmarket authored it (doc 14).",
    },
}


# ----------------------------------------------------- hand-authored verbatim quotes
# Each value is an EXACT substring of the paragraph it cites (item (j) proves this).
# Used by demo/eu_traps_build.py for the controlling-evidence / decoy display.
QUOTES: dict[tuple[str, int], str] = {
    ("35", 3): "is not a warranty or guarantee of uptime",
    ("35", 2): "monthly availability target of 99.9%",
    ("36", 2): "The outage lasted approximately 30 hours",
    ("36", 4): "the estimated gross-margin impact of the outage is approximately EUR 30,000",
    ("36", 3): "this figure is gross revenue, not margin",
    ("37", 1): "Sent: 25 October 2025, 14:10",
    ("37", 2): "treat this email as a formal warning",
    ("38", 2): "the misconfiguration was remediated the same day",
    ("39", 2): "removed from the sub-processor register on 30 November 2023",
    ("40", 2): "no EU customer personal data flows to the India environment",
    ("41", 1): "an inbound session from a Mumbai (India) IP address",
    ("41", 2): "the underlying access originated from within the EU",
    ("42", 7): "indemnify the Customer without limit",
    ("43", 11): "supersedes any prior draft, including draft v0.9",
    ("44", 2): "encrypted with AES-256",
    ("44", 3): "legacy archive tier still uses 3DES",
    ("45", 2): "reasonable security experts may differ",
    ("46", 2): "The Controller is responsible for carrying out any data protection impact "
               "assessment required by Article 35 GDPR",
    ("14", 1): "Data Protection Impact Assessment — Brightmarket analytics processing",
}


# --------------------------------------------------------------------- helpers
def para_text(bundle: dict, doc: str, para: int) -> str | None:
    """Return the verbatim text of ``(doc, para)`` in an engine-shape bundle, or None.

    ``bundle`` is ``{doc_id: {"paras": [(n, text), ...], ...}}`` (the shape
    ``compose`` returns and the engine seam consumes)."""
    entry = bundle.get(doc)
    if not entry:
        return None
    for n, text in entry.get("paras", []):
        if n == para:
            return text
    return None


def _normalize_eu_gold(pid: str, g: dict) -> dict:
    """Project an ``eu_case_gold.GOLD`` entry into the rich trap-gold schema so the
    gold-as-engine oracle can score the murky case alongside the traps. The murky
    case has no planted decoys; ``verify`` follows the honest default (UNVERIFIED /
    NOT_ADDRESSED need a human), and the band follows the verdict."""
    verdict = g.get("verdict", "UNVERIFIED")
    verify = verdict in ("UNVERIFIED", "NOT_ADDRESSED")
    band = "high" if verdict in ("SUPPORTED", "CONTRADICTED") else "low"
    return {
        "trap_type": None,
        "issue": None,
        "verdict": verdict,
        "legal_risk": g.get("legal_risk", "NONE"),
        "confidence_band": band,
        "verify": verify,
        "must_not": [],
        "operative_evidence": [tuple(a) for a in g.get("evidence", [])],
        "decoy_evidence": [],
        "acts": g.get("acts", []),
        "own_goal": False,
        "rationale": g.get("note", ""),
    }


def compose() -> tuple[list[dict], dict]:
    """Merge the murky EU case with the planted traps into one (propositions, bundle)
    pair in the engine-seam shape.

    Returns ``(propositions, bundle)`` where ``propositions`` is a list of
    ``{id, text, pleaded_at:(tab, para)}`` and ``bundle`` is
    ``{doc_id: {title, paras:[(n, text)], doc_type, party, date, category, modality}}``.
    Doc "02" (the Particulars of Claim) is extended with the trap pleadings ¶24..¶30."""
    propositions: list[dict] = []
    for p in EUG.PROPOSITIONS:
        propositions.append({"id": p.id, "text": p.text,
                             "pleaded_at": EUG.PLEADED_AT.get(p.id)})
    for tp in TRAP_PROPOSITIONS:
        propositions.append({"id": tp["id"], "text": tp["text"],
                             "pleaded_at": tp["pleaded_at"]})

    bundle: dict = {}
    for doc_id, (title, doc_type, party, date, category, modality) in EUG.DOC_META.items():
        paras = list(EUG._PARAS.get(doc_id, []))
        if doc_id == "02":
            paras = paras + [(n, t) for n, t in sorted(TRAP_PLEADED_PARAS.items())]
        if not paras:
            continue
        bundle[doc_id] = {"title": title, "paras": paras, "doc_type": doc_type,
                          "party": party, "date": date, "category": category,
                          "modality": modality}
    for doc_id, meta in TRAP_DOCS.items():
        bundle[doc_id] = {"title": meta["title"], "paras": list(meta["paras"]),
                          "doc_type": meta["doc_type"], "party": meta["party"],
                          "date": meta["date"], "category": meta["category"],
                          "modality": meta["modality"]}
    return propositions, bundle


def compose_gold() -> dict:
    """Merged rich gold for the whole composed bundle: the murky case (normalized)
    plus the planted traps. Feeds the gold-as-engine oracle and the harness's
    whole-bundle 'never SUPPORTED-high on a non-SUPPORTED proposition' property."""
    merged: dict = {}
    for pid, g in EUG.GOLD.items():
        merged[pid] = _normalize_eu_gold(pid, g)
    for pid, g in TRAP_GOLD.items():
        merged[pid] = dict(g)
    return merged
