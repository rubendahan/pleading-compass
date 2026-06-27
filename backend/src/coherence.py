"""Bundle Coherence — the second paradigm, as a seeded vertical POC.

Pleading-first (the rest of the engine) asks, for each pleaded allegation, whether
the evidence supports it. **Bundle-first** inverts the question: it asks what
*internally consistent story* the bundle itself supports, then reports which pleaded
allegations that story rejects or forces the lawyer to amend.

    LLM local, solver global.

The LLM is never asked to decide global truth. Here the global decision is made by a
deterministic, dependency-free **brute-force maximum-weight consistent-subset solver**:
each claim is a 0/1 variable, every *hard* contradiction/supersession edge forbids
accepting both endpoints, and we maximise the total source weight of the accepted set.
Higher-weight, quote-grounded evidence therefore displaces lower-weight pleaded
assertions automatically — and the rejection is explained by the conflicting edge.

**Honesty (this is a POC).** The claims are *seeded* from the committed gold anchors of
the synthetic *Meridian v TechFlow* bundle (``data/bundle_gold.py``) — real doc/¶ anchors,
verdicts and legal overlays, reused rather than re-derived. We do NOT run a general
paragraph-level claim extractor here; that LLM extractor is the future drop-in. When the
real DOCX bundle is on disk, claims are enriched with verbatim quotes checked through the
same anti-hallucination gate (``judges.base.verbatim_ok``); offline they show the anchor
only. No quote is ever invented.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .judges import base


# --------------------------------------------------------------- data shapes
@dataclass
class CoherenceClaim:
    id: str
    issue: str
    text: str
    proposition_id: Optional[str]
    source_doc: Optional[str]
    source_para: Optional[str]
    quote: Optional[str]
    source_type: str
    weight: float
    polarity: str               # "bundle" | "pleading" | "legal_overlay"
    verbatim_ok: bool = True
    meta: dict = field(default_factory=dict)


@dataclass
class CoherenceEdge:
    source: str
    target: str
    relation: str               # contradicts | supports | supersedes | caps | legal_bar | qualifies | attacks
    hard: bool
    explanation: str
    rule_id: str


@dataclass
class CoherenceCluster:
    issue: str
    claims: list[CoherenceClaim]
    edges: list[CoherenceEdge]
    meta: dict = field(default_factory=dict)   # carries seed story/amendments + gold for impacts


@dataclass
class CoherenceSolution:
    issue: str
    accepted: list[CoherenceClaim]
    rejected: list[CoherenceClaim]
    edges: list[CoherenceEdge]
    coherent_story: list[str]
    pleading_impacts: list[str]
    suggested_amendments: list[str]
    solver: str


# --------------------------------------------------------------- source weights
# Higher = harder evidence. Reused for every seeded claim; mirrors the evidence
# hierarchy the rest of the engine already trusts (signed docs > experts > witnesses
# > correspondence > pleadings).
SOURCE_WEIGHTS = {
    "signed_contract": 5.0,
    "change_order": 5.0,
    "acceptance_certificate": 5.0,
    "defect_log": 4.5,
    "expert_report": 4.0,
    "contemporaneous_email": 4.0,
    "admission": 4.0,
    "legal_clause": 4.0,
    "witness_statement": 2.0,
    "solicitor_letter": 1.5,
    "pleading": 1.0,
    "absence": 1.0,
}


def weight_for(source_type: str) -> float:
    return SOURCE_WEIGHTS.get(source_type, 1.0)


# --------------------------------------------------------------- the brute-force solver
def solve_cluster(cluster: CoherenceCluster) -> CoherenceSolution:
    """Select the maximum-weight subset of claims with no hard conflict.

    Brute force over all 2^n masks (n is tiny per cluster): a mask is valid iff no
    hard edge has both endpoints selected; we keep the valid mask of greatest total
    weight. Deterministic and dependency-free. Falls back to a greedy pass (clearly
    labelled) only if a cluster ever exceeds 20 claims — never a silent failure.
    """
    claims = cluster.claims
    n = len(claims)
    index = {c.id: i for i, c in enumerate(claims)}
    hard_pairs = [(index[e.source], index[e.target])
                  for e in cluster.edges
                  if e.hard and e.source in index and e.target in index]

    if n > 20:
        accepted_ids = _greedy(claims, hard_pairs)
        solver = "greedy_fallback"
    else:
        best_mask, best_score = 0, -1.0
        for mask in range(1 << n):
            if any((mask >> i) & 1 and (mask >> j) & 1 for i, j in hard_pairs):
                continue
            score = sum(claims[i].weight for i in range(n) if (mask >> i) & 1)
            if score > best_score:
                best_score, best_mask = score, mask
        accepted_ids = {claims[i].id for i in range(n) if (best_mask >> i) & 1}
        solver = "brute_force"

    accepted = [c for c in claims if c.id in accepted_ids]
    rejected = [c for c in claims if c.id not in accepted_ids]

    gold = cluster.meta.get("gold", {})
    return CoherenceSolution(
        issue=cluster.issue,
        accepted=accepted,
        rejected=rejected,
        edges=cluster.edges,
        coherent_story=list(cluster.meta.get("story", [])),
        pleading_impacts=_pleading_impacts(claims, accepted_ids, gold),
        suggested_amendments=list(cluster.meta.get("amendments", [])),
        solver=solver,
    )


def _greedy(claims: list[CoherenceClaim], hard_pairs: list[tuple[int, int]]) -> set[str]:
    """Fallback for oversized clusters: take claims by descending weight, skipping any
    that hard-conflict with one already taken."""
    order = sorted(range(len(claims)), key=lambda i: claims[i].weight, reverse=True)
    taken: set[int] = set()
    conflicts: dict[int, set[int]] = {}
    for i, j in hard_pairs:
        conflicts.setdefault(i, set()).add(j)
        conflicts.setdefault(j, set()).add(i)
    for i in order:
        if conflicts.get(i, set()) & taken:
            continue
        taken.add(i)
    return {claims[i].id for i in taken}


def _pleading_impacts(claims: list[CoherenceClaim], accepted_ids: set[str], gold: dict) -> list[str]:
    """For each pleaded claim, derive its fate. The verdict comes from the solver
    (rejected?) combined with the gold verdict/overlay (reused from bundle_gold, not
    re-decided), and the *why* from the gold note."""
    out: list[str] = []
    for c in claims:
        if c.polarity != "pleading" or not c.proposition_id:
            continue
        g = gold.get(c.proposition_id, {})
        overlay = g.get("legal_risk", "NONE")
        if c.id not in accepted_ids:
            verdict = "REJECTED_BY_COHERENT_STORY"
        elif g.get("verdict") == "NOT_ADDRESSED":
            verdict = "NOT_ADDRESSED"
        elif overlay and overlay != "NONE":
            verdict = "SURVIVES (LEGALLY_RISKY)"
        else:
            verdict = "SURVIVES"
        line = f"{c.proposition_id}: {verdict}"
        if overlay and overlay != "NONE":
            line += f"  [legal overlay: {overlay}]"
        if g.get("note"):
            line += f" — {g['note']}"
        out.append(line)
    return out


# --------------------------------------------------------------- seeded clusters
# Each recipe declares the POC narrative (claim text, edges, story, amendments). The
# truth-bearing labels (pleaded ¶ location, gold verdict, legal overlay, the *why*
# note) are pulled from data/bundle_gold.py at build time — reuse, not duplication.
_RECIPES: list[dict] = [
    {
        "issue": "DELAY/SCOPE",
        "story": [
            "Original contractual go-live was 1 October 2024.",
            "Meridian requested the loyalty-module change.",
            "Change Order No. 3 revised the go-live date to 18 November 2024.",
            "The Platform went live on 18 November 2024 — i.e. on the revised date.",
            "So simple lateness against the original 1 Oct date is not supported unless the "
            "pleading addresses the signed variation.",
        ],
        "amendments": [
            "Do not plead simple late delivery against the original 1 Oct date without "
            "addressing Change Order No. 3.",
            "Withdraw or qualify the 'no scope change' allegation; address Meridian's own "
            "loyalty-module request.",
        ],
        "claims": [
            {"id": "p2_late", "kind": "pleading", "prop": "P2",
             "text": "Delivered late: went live 18 Nov, seven weeks after the 1 Oct go-live date."},
            {"id": "p3_noscope", "kind": "pleading", "prop": "P3",
             "text": "Meridian requested no change to scope; all delay was TechFlow's fault."},
            {"id": "co3_revised", "kind": "bundle", "anchor": ("07", 9), "source_type": "change_order",
             "text": "Change Order No. 3 revised the contractual go-live date to 18 November 2024."},
            {"id": "loyalty_req", "kind": "bundle", "anchor": ("10", 4), "source_type": "contemporaneous_email",
             "text": "Meridian requested the loyalty-module change."},
            {"id": "actual_golive", "kind": "bundle", "anchor": ("18", 3), "source_type": "witness_statement",
             "text": "The Platform went live on 18 November 2024 — the revised date."},
        ],
        "edges": [
            {"source": "co3_revised", "target": "p2_late", "relation": "supersedes", "hard": True,
             "rule": "variation_supersedes_original_deadline",
             "explanation": "A signed variation revised the deadline to 18 Nov; lateness against "
                            "the original 1 Oct date cannot stand without addressing it."},
            {"source": "loyalty_req", "target": "p3_noscope", "relation": "contradicts", "hard": True,
             "rule": "scope_change_requested_contradicts_no_change",
             "explanation": "Meridian itself requested the loyalty-module change."},
            {"source": "co3_revised", "target": "actual_golive", "relation": "supports", "hard": False,
             "rule": "revised_date_met", "explanation": "Go-live met the revised date."},
        ],
    },
    {
        "issue": "ACCEPTANCE",
        "story": [
            "Meridian signed a Phase 1 UAT Acceptance Certificate on 12 November 2024.",
            "So the pleaded 'no acceptance / no sign-off at any time' is rejected.",
        ],
        "amendments": [
            "Withdraw or qualify the no-acceptance allegation; address the signed UAT "
            "Acceptance Certificate.",
        ],
        "claims": [
            {"id": "p7_noaccept", "kind": "pleading", "prop": "P7",
             "text": "Meridian gave no acceptance or sign-off at any time."},
            {"id": "uat_signed", "kind": "bundle", "anchor": ("08", 7), "source_type": "acceptance_certificate",
             "text": "Meridian signed a Phase 1 UAT Acceptance Certificate on 12 November 2024."},
        ],
        "edges": [
            {"source": "uat_signed", "target": "p7_noaccept", "relation": "contradicts", "hard": True,
             "rule": "signed_acceptance_contradicts_no_acceptance",
             "explanation": "A signed acceptance certificate is inconsistent with 'no acceptance'."},
        ],
    },
    {
        "issue": "OUTAGE/CAUSATION",
        "story": [
            "The pleading alleges unavailability of more than 40% of trading hours.",
            "The IT expert puts Platform-attributable unavailability at about 6.2%.",
            "The single largest outage was attributable to Meridian's own network provider.",
            "So the >40% figure and TechFlow-only causation are rejected or heavily qualified.",
        ],
        "amendments": [
            "Do not plead >40% unless further evidence exists; reduce the outage case to the "
            "expert-supported ~6.2% figure.",
            "Reframe causation to address the Meridian-network contribution.",
        ],
        "claims": [
            {"id": "p5_outage", "kind": "pleading", "prop": "P5",
             "text": "Platform unavailable for >40% of trading hours, by reason of its own defects."},
            {"id": "expert_62", "kind": "bundle", "anchor": ("19", 3), "source_type": "expert_report",
             "text": "IT expert: Platform-attributable unavailability was about 6.2%."},
            {"id": "network_cause", "kind": "bundle", "anchor": ("17", 3), "source_type": "witness_statement",
             "text": "The largest outage was attributable to Meridian's own network provider, not the Platform."},
        ],
        "edges": [
            {"source": "expert_62", "target": "p5_outage", "relation": "contradicts", "hard": True,
             "rule": "numeric_interval_disjoint",
             "explanation": "Pleaded interval [40,100]% is disjoint from the expert ~6.2% — a "
                            "numeric contradiction (cf. numeric_check)."},
            {"source": "network_cause", "target": "p5_outage", "relation": "attacks", "hard": False,
             "rule": "alternative_causation",
             "explanation": "The biggest outage attributable to Meridian's own network undermines "
                            "TechFlow-only causation."},
        ],
    },
    {
        "issue": "WARNING/CAUSATION",
        "story": [
            "TechFlow recommended in writing that go-live be deferred.",
            "Meridian's Programme Director overruled that advice and instructed go-live.",
            "So 'we warned them, they ignored us and went live' is the opposite of the record.",
        ],
        "amendments": [
            "Withdraw or recast the 'ignored our warnings' allegation: the contemporaneous "
            "record shows TechFlow advised deferral and Meridian overruled it.",
        ],
        "claims": [
            {"id": "p4_warned", "kind": "pleading", "prop": "P4",
             "text": "Meridian warned the Platform was not ready and asked to defer; TechFlow "
                     "ignored the warnings and proceeded to go-live."},
            {"id": "deferral_advice", "kind": "bundle", "anchor": ("09", 5), "source_type": "contemporaneous_email",
             "text": "TechFlow recommended in writing that go-live be deferred."},
            {"id": "overruled", "kind": "bundle", "anchor": ("16", 4), "source_type": "witness_statement",
             "text": "Meridian's Programme Director overruled the advice and instructed go-live."},
        ],
        "edges": [
            {"source": "deferral_advice", "target": "p4_warned", "relation": "contradicts", "hard": True,
             "rule": "deferral_advice_contradicts_ignored_warnings",
             "explanation": "TechFlow advised deferral in writing — the opposite of ignoring warnings."},
            {"source": "overruled", "target": "p4_warned", "relation": "attacks", "hard": False,
             "rule": "claimant_overruled_the_advice",
             "explanation": "Meridian itself overruled the advice and instructed go-live."},
        ],
    },
    {
        "issue": "DEFECTS",
        "story": [
            "The Defect Log records Severity-1 stock-synchronisation failures.",
            "The IT expert finds the stock-sync module was below standard.",
            "So the defects allegation is genuinely supported — it survives.",
        ],
        "amendments": [
            "Keep the defects allegation (P6) — it is the claimant's strongest, evidence-backed point.",
        ],
        "claims": [
            {"id": "p6_defects", "kind": "pleading", "prop": "P6",
             "text": "Severity-1 stock-sync defects; the Platform was not of satisfactory quality "
                     "nor fit for purpose."},
            {"id": "defect_log", "kind": "bundle", "anchor": ("13", 5), "source_type": "defect_log",
             "text": "The Defect Log records Severity-1 stock-synchronisation failures."},
            {"id": "expert_defects", "kind": "bundle", "anchor": ("19", 5), "source_type": "expert_report",
             "text": "The IT expert finds the stock-sync module was below standard."},
        ],
        "edges": [
            {"source": "defect_log", "target": "p6_defects", "relation": "supports", "hard": False,
             "rule": "defect_log_supports_defects",
             "explanation": "Contemporaneous Defect Log records the Severity-1 failures."},
            {"source": "expert_defects", "target": "p6_defects", "relation": "supports", "hard": False,
             "rule": "expert_supports_defects",
             "explanation": "The IT expert independently finds the module below standard."},
        ],
    },
    {
        "issue": "RECITALS",
        "story": [
            "The Particulars' factual recitals (¶3-5) are the agreed contractual background.",
            "The signed MSA (Tab 3) records that TechFlow agreed to build the Platform and was "
            "executed by both parties.",
            "The MSA incorporates the SOW (Tab 4) at Schedule 1, which sets the scope, plan and "
            "milestones.",
            "The MSA fixes the total charges at £2,400,000 (excl VAT) against milestones.",
            "So every recital is grounded in a signed contract document and is well supported.",
        ],
        "amendments": [
            "Keep the recital paragraphs (PR3-PR5) — they are agreed background, grounded in the "
            "signed MSA/SOW; annotate each as supported by the contract clause.",
        ],
        "claims": [
            {"id": "pr3_msa", "kind": "pleading", "prop": "PR3",
             "text": "TechFlow agreed under the executed MSA (14 Mar 2024) to design, build, "
                     "configure and implement the Platform."},
            {"id": "pr4_sow", "kind": "pleading", "prop": "PR4",
             "text": "The MSA incorporated the SOW at Schedule 1, setting the scope, "
                     "implementation plan and milestones."},
            {"id": "pr5_charges", "kind": "pleading", "prop": "PR5",
             "text": "The total charges payable under the MSA were £2,400,000 (excl VAT), "
                     "payable against milestones."},
            {"id": "msa_scope", "kind": "bundle", "anchor": ("03", 8), "source_type": "signed_contract",
             "text": "MSA cl 1.1: the Supplier shall design, build, configure, test and implement "
                     "the Platform in accordance with the SOW at Schedule 1 (signed by both parties)."},
            {"id": "sow_schedule", "kind": "bundle", "anchor": ("04", 4), "source_type": "signed_contract",
             "text": "SOW (Schedule 1 to the MSA): sets the scope of the works, with the "
                     "implementation timetable and payment milestones."},
            {"id": "msa_charges", "kind": "bundle", "anchor": ("03", 11), "source_type": "signed_contract",
             "text": "MSA cl 2.1: the total charges for the Services are £2,400,000 (excl VAT), "
                     "payable against the milestones set out in the SOW."},
        ],
        "edges": [
            {"source": "msa_scope", "target": "pr3_msa", "relation": "supports", "hard": False,
             "rule": "signed_contract_supports_recital",
             "explanation": "The signed MSA (cl 1.1, executed by both parties) grounds the recital "
                            "that TechFlow agreed to build the Platform."},
            {"source": "sow_schedule", "target": "pr4_sow", "relation": "supports", "hard": False,
             "rule": "sow_schedule_supports_recital",
             "explanation": "The SOW at Schedule 1 grounds the recital that the MSA incorporated the "
                            "SOW setting scope, plan and milestones."},
            {"source": "msa_charges", "target": "pr5_charges", "relation": "supports", "hard": False,
             "rule": "charges_clause_supports_recital",
             "explanation": "MSA cl 2.1 grounds the recital that the total charges were £2,400,000."},
        ],
    },
    {
        "issue": "QUANTUM/CAP",
        "story": [
            "The quantum expert accepts wasted expenditure of about £1.8m.",
            "The pleaded loss of profit of £4.2m is substantially overstated.",
            "The quantum expert supports about £1.3m of loss of profit.",
            "MSA clause 14 excludes loss of profit and caps liability near £1.8m.",
            "A DC flood and the wider market are alternative causes of the Q4 shortfall.",
        ],
        "amendments": [
            "Keep the wasted-expenditure claim (P9a) — it is supported by the quantum expert.",
            "Reduce or qualify the £4.2m loss-of-profit claim (P9b); address the expert figure, "
            "the cl.14 cap, and the alternative (flood/market) causation.",
        ],
        "claims": [
            {"id": "p9a_wasted", "kind": "pleading", "prop": "P9a",
             "text": "Wasted expenditure of £1.8m paid to TechFlow under the MSA."},
            {"id": "p9b_profit", "kind": "pleading", "prop": "P9b",
             "text": "Loss of profit of £4.2m during the Nov–Dec peak trading period."},
            {"id": "expert_wasted", "kind": "bundle", "anchor": ("20", 2), "source_type": "expert_report",
             "text": "Quantum expert accepts the ~£1.8m wasted expenditure."},
            {"id": "expert_profit", "kind": "bundle", "anchor": ("20", 4), "source_type": "expert_report",
             "text": "Quantum expert puts supportable loss of profit at about £1.3m."},
            {"id": "flood_market", "kind": "bundle", "anchor": ("20", 6), "source_type": "expert_report",
             "text": "Much of the Q4 shortfall is attributable to a DC flood and the wider market."},
            {"id": "cap_cl14", "kind": "legal_overlay", "anchor": ("03", 14), "source_type": "legal_clause",
             "text": "MSA clause 14 excludes loss of profit and caps liability near £1.8m."},
        ],
        "edges": [
            {"source": "expert_wasted", "target": "p9a_wasted", "relation": "supports", "hard": False,
             "rule": "expert_supports_wasted_expenditure",
             "explanation": "The quantum expert supports the ~£1.8m wasted expenditure."},
            {"source": "expert_profit", "target": "p9b_profit", "relation": "contradicts", "hard": True,
             "rule": "numeric_interval_disjoint",
             "explanation": "Pleaded £4.2m is disjoint from the expert-supported ~£1.3m."},
            {"source": "cap_cl14", "target": "p9b_profit", "relation": "caps", "hard": False,
             "rule": "contractual_cap_overlay",
             "explanation": "cl.14 caps recovery — a legal overlay, not a factual contradiction."},
            {"source": "flood_market", "target": "p9b_profit", "relation": "qualifies", "hard": False,
             "rule": "alternative_causation",
             "explanation": "Flood/market are alternative causes of the Q4 shortfall."},
        ],
    },
    {
        "issue": "TRAINING",
        "story": [
            "SOW clause 3.2 makes training of Meridian's own staff Meridian's responsibility.",
            "TechFlow's only training obligation was a train-the-trainer session and written "
            "user guides.",
            "So 'TechFlow failed to provide adequate training' is contradicted by the contract, "
            "unless Meridian pleads a specific failure of the train-the-trainer / user-guide duty.",
        ],
        "amendments": [
            "Withdraw or recast the training allegation: SOW cl 3.2 puts staff training on "
            "Meridian; plead only a failure of TechFlow's limited train-the-trainer / user-guide "
            "obligation, if evidenced. Lawyer review required.",
        ],
        "claims": [
            {"id": "p8_training", "kind": "pleading", "prop": "P8",
             "text": "TechFlow failed to provide adequate training to Meridian's staff."},
            {"id": "sow_training_alloc", "kind": "bundle", "anchor": ("04", 9),
             "source_type": "signed_contract",
             "text": "SOW cl 3.2: training of the Customer's staff is the Customer's "
                     "responsibility; the Supplier owed only a train-the-trainer session and "
                     "written user guides."},
        ],
        "edges": [
            {"source": "sow_training_alloc", "target": "p8_training", "relation": "contradicts",
             "hard": True, "rule": "contractual_allocation_contradicts_training_failure",
             "explanation": "SOW cl 3.2 allocates staff training to Meridian and limits TechFlow's "
                            "duty to a train-the-trainer session and written guides — contradicting "
                            "'TechFlow failed to provide adequate training'."},
        ],
    },
    {
        "issue": "ORAL_REP/NON_RELIANCE",
        "story": [
            "No document in the bundle evidences the alleged pre-contract oral representation.",
            "MSA clause 22 (entire agreement / non-reliance) would in any event bar reliance.",
            "This is a legal risk overlay, not a factual contradiction.",
        ],
        "amendments": [
            "Do not treat non-reliance as a factual contradiction; mark the representation claim "
            "as not addressed plus a contractual reliance blocker. Lawyer review required.",
        ],
        "claims": [
            {"id": "p1_oralrep", "kind": "pleading", "prop": "P1",
             "text": "Pre-contract oral representation of 10,000 concurrent transactions, false."},
            {"id": "absence_rep", "kind": "absence",
             "text": "No document evidences the alleged pre-contract representation."},
            {"id": "nonreliance_cl22", "kind": "legal_overlay", "anchor": ("03", 22), "source_type": "legal_clause",
             "text": "MSA cl.22 (entire agreement / non-reliance) bars reliance on pre-contract representations."},
        ],
        "edges": [
            {"source": "nonreliance_cl22", "target": "p1_oralrep", "relation": "legal_bar", "hard": False,
             "rule": "non_reliance_legal_bar",
             "explanation": "A non-reliance clause is a legal blocker, not a factual contradiction."},
        ],
    },
]


def _build_claim(cdef: dict, issue: str, gold: dict, pleaded_at: dict, bundle) -> CoherenceClaim:
    kind = cdef["kind"]
    pid = cdef.get("prop")
    if kind == "pleading":
        anchor = pleaded_at.get(pid)
        doc, para = (anchor if anchor else (None, None))
        source_type, polarity = "pleading", "pleading"
    elif kind == "legal_overlay":
        doc, para = cdef["anchor"]
        source_type, polarity = cdef.get("source_type", "legal_clause"), "legal_overlay"
    elif kind == "absence":
        doc, para = None, None
        source_type, polarity = "absence", "bundle"
    else:  # bundle evidence
        doc, para = cdef["anchor"]
        source_type, polarity = cdef["source_type"], "bundle"

    weight = weight_for(source_type)
    quote: Optional[str] = None
    verbatim = True
    quote_status = "anchored_not_loaded" if doc is not None else "no_anchor"

    # Enrich with a verbatim quote only when the real bundle is on disk; the quote is
    # checked through the same anti-hallucination gate the judges use. Never invented.
    if bundle is not None and doc is not None and para is not None:
        d = bundle.get(doc)
        p = d.para(int(para)) if d else None
        if p:
            if base.verbatim_ok(p.text, bundle, doc):
                quote, verbatim, quote_status = p.text, True, "loaded"
            else:                                   # should not happen; fail safe, no quote shown
                quote, verbatim, weight, quote_status = None, False, 0.0, "unverified"

    return CoherenceClaim(
        id=cdef["id"], issue=issue, text=cdef["text"], proposition_id=pid,
        source_doc=doc, source_para=(str(para) if para is not None else None),
        quote=quote, source_type=source_type, weight=weight, polarity=polarity,
        verbatim_ok=verbatim, meta={"quote_status": quote_status},
    )


def build_seeded_coherence_clusters(bundle=None, gold: Optional[dict] = None,
                                    pleaded_at: Optional[dict] = None) -> list[CoherenceCluster]:
    """Build the seeded coherence clusters. Anchors, gold verdicts and legal overlays
    come from ``data/bundle_gold.py`` (reused); quotes are added only if *bundle* is
    on disk."""
    if gold is None or pleaded_at is None:
        from data.bundle_gold import GOLD, PLEADED_AT
        gold = gold if gold is not None else GOLD
        pleaded_at = pleaded_at if pleaded_at is not None else PLEADED_AT

    clusters: list[CoherenceCluster] = []
    for recipe in _RECIPES:
        claims = [_build_claim(c, recipe["issue"], gold, pleaded_at, bundle)
                  for c in recipe["claims"]]
        edges = [CoherenceEdge(e["source"], e["target"], e["relation"], e["hard"],
                               e.get("explanation", ""), e.get("rule", ""))
                 for e in recipe["edges"]]
        clusters.append(CoherenceCluster(
            issue=recipe["issue"], claims=claims, edges=edges,
            meta={"story": recipe["story"], "amendments": recipe["amendments"], "gold": gold}))
    return clusters


def analyse(bundle=None, gold: Optional[dict] = None,
            pleaded_at: Optional[dict] = None) -> list[CoherenceSolution]:
    """Build the seeded clusters and solve each one. Runs fully offline."""
    return [solve_cluster(c) for c in build_seeded_coherence_clusters(bundle, gold, pleaded_at)]


# --------------------------------------------------------------- sensitivity
@dataclass
class Sensitivity:
    """What a pleaded outcome depends on — the lawyer's 'what could break this?'.

    ``load_bearing`` maps each surviving pleaded claim to the accepted bundle claims that
    support it (its single point(s) of failure); ``single_source`` lists the ones resting on
    exactly one source. ``revives_if_removed`` maps an accepted claim to the rejected pleaded
    claims that would come back if it were discredited — i.e. the smallest evidence the other
    side must attack to revive a point (or, read the other way, what is holding it down).
    """
    issue: str
    load_bearing: dict[str, list[str]]
    single_source: list[str]
    revives_if_removed: dict[str, list[str]]


def _without(cluster: CoherenceCluster, claim_id: str) -> CoherenceCluster:
    return CoherenceCluster(
        issue=cluster.issue,
        claims=[c for c in cluster.claims if c.id != claim_id],
        edges=[e for e in cluster.edges if e.source != claim_id and e.target != claim_id],
        meta=cluster.meta,
    )


def sensitivity(cluster: CoherenceCluster) -> Sensitivity:
    """Deterministic sensitivity sweep: re-solve the cluster with each claim removed.

    No LLM, no extra data — just the solver run once per claim. Reveals load-bearing support
    and the minimal discredit that flips a rejected pleaded point back in."""
    base_accepted = {c.id for c in solve_cluster(cluster).accepted}
    pleadings = [c for c in cluster.claims if c.polarity == "pleading"]

    load_bearing: dict[str, list[str]] = {}
    for p in pleadings:
        supporters = [e.source for e in cluster.edges
                      if e.relation == "supports" and e.target == p.id and e.source in base_accepted]
        if supporters:
            load_bearing[p.id] = supporters
    single_source = [pid for pid, s in load_bearing.items() if len(s) == 1]

    revives: dict[str, list[str]] = {}
    for c in cluster.claims:
        reduced = {x.id for x in solve_cluster(_without(cluster, c.id)).accepted}
        flipped = [p.id for p in pleadings
                   if p.id != c.id and p.id not in base_accepted and p.id in reduced]
        if flipped:
            revives[c.id] = flipped

    return Sensitivity(cluster.issue, load_bearing, single_source, revives)


def analyse_sensitivity(bundle=None, gold: Optional[dict] = None,
                        pleaded_at: Optional[dict] = None) -> list[Sensitivity]:
    """Run the sensitivity sweep over every seeded cluster (offline, deterministic)."""
    return [sensitivity(c) for c in build_seeded_coherence_clusters(bundle, gold, pleaded_at)]


# --------------------------------------------------------------- plain-text render
def render_cli(solutions: list[CoherenceSolution]) -> str:
    """Plain-text render of the strongest coherent story per issue + pleading impact."""
    out = ["Bundle Coherence — the strongest internally consistent story the bundle supports",
           "(seeded vertical POC over the synthetic bundle; LLM local, solver global)", ""]
    for s in solutions:
        out.append(f"■ {s.issue}   [{s.solver}]")
        for line in s.coherent_story:
            out.append(f"    · {line}")
        if s.rejected:
            out.append("  Rejected / risky pleaded claims:")
            for c in s.rejected:
                if c.polarity == "pleading":
                    out.append(f"    ✗ [{c.proposition_id or c.id}] {c.text}")
        if s.pleading_impacts:
            out.append("  Pleading impact:")
            for imp in s.pleading_impacts:
                out.append(f"    → {imp}")
        if s.suggested_amendments:
            out.append("  Suggested amendment (lawyer review required):")
            for a in s.suggested_amendments:
                out.append(f"    ✎ {a}")
        out.append("")
    return "\n".join(out)


# --------------------------------------------------------------- Cypher export
def coherence_to_cypher(solutions: list[CoherenceSolution]) -> str:
    """Idempotent MERGE statements for the coherence graph — twin of ``graph.to_cypher``.

    One ``Claim`` node per claim (carrying the solver's accepted/rejected verdict, so
    Neo4j can colour the strongest coherent story) and one typed relationship per edge
    (CONTRADICTS / SUPERSEDES / CAPS / …). Reuses graph's value escaper for consistency.
    """
    from .graph import _cy

    accepted_ids = {c.id for s in solutions for c in s.accepted}
    lines = ["// Bundle Coherence graph — claims + relations, with the solver's verdict"]
    seen: set[str] = set()
    for s in solutions:
        for c in s.accepted + s.rejected:
            if c.id in seen:
                continue
            seen.add(c.id)
            props = {
                "id": c.id, "issue": c.issue, "text": c.text, "source_type": c.source_type,
                "weight": c.weight, "polarity": c.polarity,
                "proposition_id": c.proposition_id or "",
                "anchor": f"{c.source_doc}¶{c.source_para}" if c.source_doc else "",
                "accepted": c.id in accepted_ids,
                "verdict": "accepted" if c.id in accepted_ids else "rejected",
            }
            body = ", ".join(f"{k}: {_cy(v)}" for k, v in props.items())
            lines.append(f'MERGE (n:Claim {{id: {_cy(c.id)}}}) SET n += {{{body}}};')
        for e in s.edges:
            lines.append(
                f'MATCH (a {{id: {_cy(e.source)}}}), (b {{id: {_cy(e.target)}}}) '
                f'MERGE (a)-[r:{e.relation.upper()}]->(b) '
                f'SET r += {{hard: {_cy(e.hard)}, rule: {_cy(e.rule_id)}}};')
    return "\n".join(lines)
