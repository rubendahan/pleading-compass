from src.ingest import load_bundle
from src.pleadings import seed_propositions
from src.judges.stub import judge

BUNDLE = "data/selftest/bundle"


def _props():
    return {p.id: p for p in seed_propositions()}


def test_stub_matches_gold_p2():
    b = load_bundle(BUNDLE)
    jP2 = judge(_props()["P2"], b)
    assert jP2.verdict == "SUPPORTED"
    assert jP2.single_source is True                     # rests on the Fujitsu engineer only
    assert jP2.contradictions                            # P2 contradicts the Defence (D2)
    for ev in jP2.evidence:                              # quotes are verbatim & anchored
        assert ev.quote and ev.doc_id and ev.para


def test_stub_gap_is_not_addressed():
    b = load_bundle(BUNDLE)
    jG1 = judge(_props()["G1"], b)
    assert jG1.verdict == "NOT_ADDRESSED" and jG1.evidence == []
    assert jG1.extra.get("note")


def test_stub_contradiction_links_04_and_02():
    b = load_bundle(BUNDLE)
    jD2 = judge(_props()["D2"], b)
    assert jD2.verdict == "CONTRADICTED"
    refs = jD2.contradictions[0].ref_a + jD2.contradictions[0].ref_b
    assert "04" in refs and "02" in refs
