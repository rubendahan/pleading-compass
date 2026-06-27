from src.models import Para, Document, Bundle, EvidenceItem, Judgement


def test_bundle_iter_and_fulltext():
    d = Document(id="01", title="Particulars", doc_type="pleading", party="claimant",
                 date="2018-01-01", paras=[Para(1, "Horizon had bugs."), Para(2, "PO could edit remotely.")])
    b = Bundle(docs=[d])
    assert b.get("01") is d
    assert list(b.iter_paras()) == [("01", 1, "Horizon had bugs."), ("01", 2, "PO could edit remotely.")]
    assert "¶1 Horizon had bugs." in b.full_text()


def test_judgement_shape():
    j = Judgement("P1", "SUPPORTED", 0.9,
                  [EvidenceItem("05", 3, "bug", "support", "expert_opinion", "high")],
                  [], single_source=False, burden="claimant", backend="stub")
    assert j.verdict == "SUPPORTED" and j.evidence[0].para == 3
