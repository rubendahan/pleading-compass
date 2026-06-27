from src.ingest import load_bundle
from src.pleadings import seed_propositions, extract_propositions

BUNDLE = "data/selftest/bundle"


def test_seed_propositions():
    props = seed_propositions()
    ids = {p.id for p in props}
    assert {"P1", "P2", "P3", "D1", "D2", "G1"} <= ids
    assert len(props) >= 6


def test_extract_offline_returns_seed():
    b = load_bundle(BUNDLE)
    assert extract_propositions(b, force_stub=True) == seed_propositions()
