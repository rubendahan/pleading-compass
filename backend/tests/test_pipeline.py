from src.ingest import load_bundle
from src.pleadings import seed_propositions
from src.pipeline import analyze
from src.judges.stub import judge

BUNDLE = "data/selftest/bundle"


def test_pipeline_stub_claimant():
    b = load_bundle(BUNDLE)
    res = analyze(b, seed_propositions(), judge, side="claimant")
    assert isinstance(res["readiness"]["overall"], int)
    assert len(res["judgements"]) == 6
    # the headline P2↔D2 cross-document contradiction (04¶2 ⟷ 02¶3) is present;
    # the contradicted defence D1 also surfaces (pleaded 02¶2 vs the expert at 05¶3)
    pairs = [{c["ref_a"], c["ref_b"]} for c in res["contradictions"]]
    assert {"04¶2", "02¶3"} in pairs
    assert all(len({ref.split("¶")[0] for ref in pair}) == 2 for pair in pairs)  # all cross-doc
    # opponent's contradicted defence D2 surfaces as a cross-exam point
    assert any(p["target_prop_id"] == "D2" for p in res["cross_exam"])
    # claimant's unaddressed P3 surfaces as a gap; P2 is load-bearing
    assert any(g["prop_id"] == "P3" for g in res["gaps"])
    assert any(lb["prop_id"] == "P2" for lb in res["load_bearing"])
