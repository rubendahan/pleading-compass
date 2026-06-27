from src.ingest import load_bundle

BUNDLE = "data/selftest/bundle"


def test_load_selftest_bundle():
    b = load_bundle(BUNDLE)
    ids = {d.id for d in b.docs}
    assert {"01", "02", "03", "04", "05", "06"} <= ids
    d04 = b.get("04")
    assert d04.doc_type == "witness" and d04.party == "defendant"
    assert d04.paras[0].n == 1 and len(d04.paras) >= 2
    # README.md is ignored
    assert all("readme" not in d.title.lower() for d in b.docs)
