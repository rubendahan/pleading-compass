"""Deterministic, offline numeric reconciliation — tests.

The z3-specific assertions skip if the solver is unavailable (``importorskip``);
the interval path runs everywhere and must reach the SAME verdict — that
equivalence is the whole point, and it keeps coverage alive in z3-less CI.
"""
from __future__ import annotations

import pytest

from src.numeric_check import (
    AVAILABILITY,
    DISPUTED_PAIRS,
    LOSS_OF_PROFIT,
    WASTED_EXPENDITURE,
    cap_analysis,
    reconcile,
    render,
    run_numeric_check,
)


# ------------------------------------------------------------------ z3 path
def test_availability_contradicted_by_z3():
    pytest.importorskip("z3")  # only assert the z3 branch where z3 is installed
    r = reconcile(AVAILABILITY)
    assert r.status == "CONTRADICTED"
    assert r.solver == "z3"
    # The pleaded > 40% (02¶11) cannot be reconciled with the IT expert's ~6.2% (19¶3).
    assert r.pleaded_anchor == "02¶11"
    assert r.evidence_anchor == "19¶3"
    assert "02¶11" in r.note and "19¶3" in r.note


def test_loss_of_profit_contradicted_by_z3():
    pytest.importorskip("z3")
    r = reconcile(LOSS_OF_PROFIT)
    assert r.status == "CONTRADICTED"
    assert r.solver == "z3"
    assert {r.pleaded_anchor, r.evidence_anchor} == {"02¶15", "20¶4"}
    assert "02¶15" in r.note and "20¶4" in r.note


# ------------------------------------------------- deterministic interval path
def test_interval_path_matches_z3_verdict():
    # Runs even where z3 is absent: same CONTRADICTED verdict, ``interval`` solver.
    for claim, anchors in (
        (AVAILABILITY, {"02¶11", "19¶3"}),
        (LOSS_OF_PROFIT, {"02¶15", "20¶4"}),
    ):
        r = reconcile(claim, use_z3=False)
        assert r.status == "CONTRADICTED"
        assert r.solver == "interval"
        assert {r.pleaded_anchor, r.evidence_anchor} == anchors


def test_both_solvers_agree_on_whole_dataset():
    pytest.importorskip("z3")
    z3_status = {r.label: r.status for r in run_numeric_check(use_z3=True)}
    iv_status = {r.label: r.status for r in run_numeric_check(use_z3=False)}
    assert z3_status == iv_status
    assert all(r.solver == "z3" for r in run_numeric_check(use_z3=True))


# ------------------------------------------------------------------ cap math
def test_cap_analysis_math():
    cap = cap_analysis()
    assert cap["claimed_total"] == 6_000_000      # 1.8m wasted + 4.2m loss of profit
    assert cap["cap"] == 1_800_000
    assert cap["recoverable"] == 1_800_000        # min(claimed_total, cap)
    assert "03¶14" in cap["note"]                 # MSA cl.14 anchor


# --------------------------------------------------------------- consistency
def test_consistent_pair_interval():
    r = reconcile(WASTED_EXPENDITURE, use_z3=False)
    assert r.status == "CONSISTENT"
    assert r.solver == "interval"


def test_consistent_pair_z3():
    pytest.importorskip("z3")
    r = reconcile(WASTED_EXPENDITURE)
    assert r.status == "CONSISTENT"
    assert r.solver == "z3"


# ------------------------------------------------------------------- render
def test_render_is_anchored_and_nonempty():
    text = render(run_numeric_check())
    assert text
    assert "CONTRADICTED" in text
    assert "19¶3" in text          # an anchor survives into the rendered output


def test_dataset_has_three_contradictions():
    runs = run_numeric_check()
    contradicted = [r for r in runs if r.status == "CONTRADICTED"]
    assert len(DISPUTED_PAIRS) == len(runs)
    assert len(contradicted) == 3  # availability, loss of profit, damages cap
