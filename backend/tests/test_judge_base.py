from src.ingest import load_bundle
from src.judges import base
from src.models import EvidenceItem

BUNDLE = "data/selftest/bundle"


def test_anchor():
    assert base.make_anchor("04", 3) == "04¶3"


def test_verbatim_ok():
    b = load_bundle(BUNDLE)
    assert base.verbatim_ok("insert and edit balancing transactions", b, "04") is True
    assert base.verbatim_ok("Post Office never made any remote edits whatsoever", b, "04") is False


def test_single_source():
    one = [EvidenceItem("04", 2, "x", "support", "witness_recollection", "medium")]
    two = one + [EvidenceItem("05", 3, "y", "support", "expert_opinion", "medium")]
    assert base.is_single_source(one) is True
    assert base.is_single_source(two) is False
