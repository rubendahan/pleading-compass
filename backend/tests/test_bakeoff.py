from src.ingest import load_bundle
from src.pleadings import seed_propositions
from src.bakeoff import score_judge, run_bakeoff
from src.judges.stub import judge
from data.selftest.propositions import GOLD

BUNDLE = "data/selftest/bundle"


def test_stub_scores_perfect():
    b = load_bundle(BUNDLE)
    row = score_judge("stub", judge, b, seed_propositions(), GOLD)
    assert row["verdict_accuracy"] == 1.0
    assert row["detects_P2_D2"] is True
    assert row["gaps_correct"] == 2
    assert row["support_false_pos"] == 0
    assert row["anchored_verbatim"] is True
    assert row["practitioner_output"] is True


def test_run_bakeoff_includes_stub():
    rows = run_bakeoff(["stub"], force_stub=True)
    assert rows and rows[0]["name"] == "stub" and rows[0]["verdict_accuracy"] == 1.0
