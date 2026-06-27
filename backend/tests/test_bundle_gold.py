"""Real-bundle answer key: the stub must reproduce the labelled analysis exactly,
which both validates the scorer on real anchors and powers the offline demo.

Skipped automatically if the gitignored DOCX bundle is not present on disk.
"""
from __future__ import annotations

import os

import pytest

from src import answer_key, ingest
from src.bakeoff import score_judge
from src.judges import get_judge

_BUNDLE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bundle")
_HAVE_BUNDLE = any(f.endswith(".docx") for f in (os.listdir(_BUNDLE) if os.path.isdir(_BUNDLE) else []))

pytestmark = pytest.mark.skipif(not _HAVE_BUNDLE, reason="real CMS bundle (.docx) not on disk")


def _setup():
    key = answer_key.bundle_key()
    bundle = ingest.load_bundle(key.bundle_dir)
    judge = get_judge("stub", key=key)
    return key, bundle, judge


def test_stub_reproduces_bundle_gold_perfectly():
    key, bundle, judge = _setup()
    row = score_judge("stub", judge, bundle, key.propositions, key.gold)
    assert row["verdict_accuracy"] == 1.0           # scorer validated on the real anchors
    assert row["detects_P2_D2"] is True             # cross-document contradictions present
    assert row["gaps_correct"] == row["gaps_total"] == 1   # P1 (misrep) only; P8 now contradicted by SOW cl 3.2
    assert row["support_false_pos"] == 0
    assert row["anchored_verbatim"] is True          # every quote verbatim in its document


def test_headline_contradiction_is_cross_document():
    key, bundle, judge = _setup()
    props = {p.id: p for p in key.propositions}
    # P4: pleaded "TechFlow ignored warnings" vs the go-live email + Vance's own statement
    jP4 = judge(props["P4"], bundle)
    assert jP4.verdict == "CONTRADICTED" and jP4.contradictions
    c = jP4.contradictions[0]
    assert c.ref_a.startswith("02") and c.ref_b.split("¶")[0] != "02"   # pleading vs evidence doc
    # P7 acceptance contradiction rests on the signed UAT certificate (doc 08)
    jP7 = judge(props["P7"], bundle)
    assert any("08" in (e.doc_id) for e in jP7.evidence)


def test_gaps_have_no_evidence_but_carry_a_note():
    key, bundle, judge = _setup()
    props = {p.id: p for p in key.propositions}
    for pid in ("P1",):   # P8 is no longer a gap — it is contradicted by SOW cl 3.2 (doc 04 ¶9)
        j = judge(props[pid], bundle)
        assert j.verdict == "NOT_ADDRESSED" and j.evidence == [] and j.extra.get("note")


def test_legal_risk_overlay_is_a_second_axis():
    key, bundle, judge = _setup()
    props = {p.id: p for p in key.propositions}
    # evidential outcome and legal defeat are distinct axes
    assert judge(props["P1"], bundle).extra.get("legal_risk") == "CONTRACTUALLY_BARRED"   # NOT_ADDRESSED but barred
    assert judge(props["P2"], bundle).extra.get("legal_risk") == "SUPERSEDED"             # date varied by Change Order
    assert judge(props["P9b"], bundle).extra.get("legal_risk") == "CAPPED"                # cl.14 cap/exclusion
    assert "legal_risk" not in judge(props["P6"], bundle).extra                            # NONE -> omitted
