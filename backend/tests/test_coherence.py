"""Tests for the Bundle Coherence POC (src/coherence.py).

The seeded clusters are built from the committed ``data/bundle_gold.py`` anchors,
so these tests run fully offline with NO API key and WITHOUT the gitignored DOCX
bundle on disk. We assert the deterministic brute-force solver selects the
maximum-weight consistent set of claims and that the strongest coherent story
rejects the right pleaded allegations.
"""
from __future__ import annotations

from src import coherence


def _by_issue() -> dict:
    return {s.issue: s for s in coherence.analyse()}


def _ids(claims) -> set:
    return {c.id for c in claims}


def test_coherence_solver_accepts_high_weight_claim():
    """A low-weight pleaded claim hard-contradicted by a high-weight expert
    claim must lose: the solver accepts the expert, rejects the pleading."""
    low = coherence.CoherenceClaim(
        id="low", issue="X", text="pleaded thing", proposition_id="P",
        source_doc=None, source_para=None, quote=None,
        source_type="pleading", weight=1.0, polarity="pleading")
    high = coherence.CoherenceClaim(
        id="high", issue="X", text="expert thing", proposition_id=None,
        source_doc="19", source_para="3", quote=None,
        source_type="expert_report", weight=4.0, polarity="bundle")
    edge = coherence.CoherenceEdge(
        source="high", target="low", relation="contradicts", hard=True,
        explanation="disjoint", rule_id="test")
    cluster = coherence.CoherenceCluster(issue="X", claims=[low, high], edges=[edge])

    sol = coherence.solve_cluster(cluster)

    assert "high" in _ids(sol.accepted)
    assert "low" in _ids(sol.rejected)
    assert sol.solver == "brute_force"


def test_delay_scope_cluster_rejects_p2_p3():
    sol = _by_issue()["DELAY/SCOPE"]
    rejected = _ids(sol.rejected)
    accepted = _ids(sol.accepted)
    assert {"p2_late", "p3_noscope"} <= rejected
    assert {"co3_revised", "loyalty_req"} <= accepted


def test_acceptance_cluster_rejects_no_acceptance():
    sol = _by_issue()["ACCEPTANCE"]
    assert "uat_signed" in _ids(sol.accepted)
    assert "p7_noaccept" in _ids(sol.rejected)


def test_outage_cluster_rejects_40_percent():
    sol = _by_issue()["OUTAGE/CAUSATION"]
    assert "expert_62" in _ids(sol.accepted)
    assert "p5_outage" in _ids(sol.rejected)


def test_quantum_cluster_keeps_p9a_rejects_p9b():
    sol = _by_issue()["QUANTUM/CAP"]
    accepted = _ids(sol.accepted)
    rejected = _ids(sol.rejected)
    assert "p9a_wasted" in accepted          # supported wasted expenditure survives
    assert "p9b_profit" in rejected          # overstated loss of profit is rejected
    # the contractual cap appears as a legal overlay, not a factual rejection
    assert any(c.polarity == "legal_overlay" for c in sol.accepted)
    assert any(e.relation == "caps" for e in sol.edges)


def test_training_cluster_is_a_contractual_contradiction():
    """P8 is not an evidence gap: SOW cl 3.2 (a signed contract) allocates staff training to
    Meridian and limits TechFlow's duty — a hard contradiction the lawyer caught that the
    'absence' heuristic had missed."""
    sol = _by_issue()["TRAINING"]
    assert any(e.hard and e.relation == "contradicts" for e in sol.edges)
    assert "sow_training_alloc" in _ids(sol.accepted)   # the high-weight contract clause wins
    assert "p8_training" in _ids(sol.rejected)           # the pleaded failure is rejected
    blob = " ".join(sol.pleading_impacts + sol.suggested_amendments).lower()
    assert "training" in blob


def test_every_displayed_quote_is_verbatim_or_absent():
    """Anti-hallucination: a claim may carry no quote (anchor only), but if it
    carries a quote it must be flagged verified — never an invented quote."""
    for sol in coherence.analyse():
        for c in sol.accepted + sol.rejected:
            if c.quote:
                assert c.verbatim_ok, f"{c.id} shows an unverified quote"


def test_all_five_required_clusters_present():
    issues = {s.issue for s in coherence.analyse()}
    assert {"DELAY/SCOPE", "ACCEPTANCE", "OUTAGE/CAUSATION",
            "QUANTUM/CAP", "TRAINING"} <= issues


def test_defects_cluster_p6_survives():
    """The tool is not a wrecking ball: a genuinely supported allegation survives."""
    sol = _by_issue()["DEFECTS"]
    assert "p6_defects" in _ids(sol.accepted)
    assert sol.rejected == []                    # nothing contradicts a supported claim


def test_warning_cluster_rejects_p4():
    sol = _by_issue()["WARNING/CAUSATION"]
    assert "p4_warned" in _ids(sol.rejected)
    assert "deferral_advice" in _ids(sol.accepted)


def test_all_propositions_covered():
    """Every substantive pleaded paragraph is accounted for — the ten disputed
    allegations and the three factual recitals (PR3-PR5)."""
    props = {c.proposition_id for s in coherence.analyse()
             for c in (s.accepted + s.rejected) if c.polarity == "pleading"}
    assert {"P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9a", "P9b",
            "PR3", "PR4", "PR5"} <= props


def test_recitals_cluster_supports_all_three():
    """The factual recitals each survive on a signed-contract supporting claim."""
    sol = _by_issue()["RECITALS"]
    accepted = _ids(sol.accepted)
    # all three recital pleadings survive (no contradiction)
    assert {"pr3_msa", "pr4_sow", "pr5_charges"} <= accepted
    assert sol.rejected == []
    # each rests on a high-weight signed-contract bundle claim via a supports edge
    assert {"msa_scope", "sow_schedule", "msa_charges"} <= accepted
    supports = {(e.source, e.target) for e in sol.edges if e.relation == "supports"}
    assert ("msa_scope", "pr3_msa") in supports
    assert ("sow_schedule", "pr4_sow") in supports
    assert ("msa_charges", "pr5_charges") in supports
    # the pleading impact reports them as surviving (supported, no legal risk)
    blob = " ".join(sol.pleading_impacts)
    assert "PR3: SURVIVES" in blob and "PR5: SURVIVES" in blob


def test_sensitivity_flags_load_bearing_and_single_source():
    s = {x.issue: x for x in coherence.analyse_sensitivity()}
    # P9a survives on a single expert source -> single point of failure
    assert s["QUANTUM/CAP"].load_bearing.get("p9a_wasted") == ["expert_wasted"]
    assert "p9a_wasted" in s["QUANTUM/CAP"].single_source
    # P6 rests on two independent sources -> not single-source
    assert set(s["DEFECTS"].load_bearing.get("p6_defects", [])) == {"defect_log", "expert_defects"}
    assert "p6_defects" not in s["DEFECTS"].single_source


def test_sensitivity_reports_what_revives_a_rejected_pleading():
    """Smallest attack: discredit the blocking claim and the rejected pleading revives."""
    s = {x.issue: x for x in coherence.analyse_sensitivity()}
    assert "p5_outage" in s["OUTAGE/CAUSATION"].revives_if_removed.get("expert_62", [])
    assert "p7_noaccept" in s["ACCEPTANCE"].revives_if_removed.get("uat_signed", [])


def test_coherence_cypher_export_is_well_formed():
    cy = coherence.coherence_to_cypher(coherence.analyse())
    assert "MERGE (n:Claim" in cy
    # the seven relation types surface as Neo4j relationship types
    assert "CONTRADICTS" in cy and "SUPERSEDES" in cy and "CAPS" in cy
    assert cy.strip().endswith(";")               # every statement terminated
    # the solver verdict travels onto the node so Neo4j can colour accepted vs rejected
    assert "accepted" in cy
