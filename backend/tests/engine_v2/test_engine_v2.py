"""engine_v2 — offline pipeline tests on the Meridian bundle + safety fixtures.

All tests run FULLY OFFLINE: deterministic stub, no ANTHROPIC_API_KEY, no network.
Asserts: (a) coverage incl. an explicit status for 02¶6; (b) every quote verbatim;
(c) AppData enums valid; (d) the safety net fires (verify + proposition.source=="ai")
on a synthetic single-source fixture.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_v2 import api, safety
from engine_v2.models import OVERLAYS, VERDICTS
from engine_v2.verify_output import check_enums, check_verbatim, synthetic_fixture

_ROOT = Path(__file__).resolve().parents[2]


def _meridian():
    """Bundle (from demo/data.json bodies) + propositions (from data/bundle_gold)."""
    data = json.loads((_ROOT / "demo" / "data.json").read_text(encoding="utf-8"))
    bundle = {}
    for tab, d in data["documents"].items():
        bundle[tab] = {
            "doc_type": d["doc_type"], "party": d["party"], "title": d["title"],
            "date": d.get("date"), "category": d.get("category"),
            "paras": [(p["n"], p["text"]) for p in d["paras"]],
        }
    from data.bundle_gold import PLEADED_AT, PROPOSITIONS
    props = [{"id": p.id, "text": p.text, "pleaded_at": PLEADED_AT[p.id]}
             for p in PROPOSITIONS]
    return props, bundle


@pytest.fixture(scope="module")
def appdata():
    props, bundle = _meridian()
    return api.to_appdata(props, bundle, offline=True)


# --------------------------------------------------------------------- (a) coverage
def test_coverage_invariant_holds(appdata):
    safety.assert_coverage(appdata)  # raises if any pleading paragraph lacks a status


def test_every_pleading_paragraph_has_a_status(appdata):
    doc02 = appdata["documents"]["02"]
    claims = {n["anchor"]: n for n in appdata["nodes"]
             if n["layer"] == "claim" and n.get("polarity") == "pleading"}
    props = {n["label"]: n for n in appdata["nodes"] if n["layer"] == "proposition"}
    for para in doc02["paras"]:
        anchor = f"02¶{para['n']}"
        hits = [c for a, c in claims.items() if a == anchor]
        assert hits, f"{anchor} has no pleading claim"
        assert any(props[c["prop"]]["verdict"] in VERDICTS for c in hits), anchor


def test_explicit_status_for_02_6(appdata):
    """The 02¶6 bug must be unreachable: it carries a verdict like any other ¶."""
    claims = [n for n in appdata["nodes"]
              if n["layer"] == "claim" and n.get("anchor") == "02¶6"]
    assert claims, "02¶6 has no pleading claim"
    props = {n["label"]: n for n in appdata["nodes"] if n["layer"] == "proposition"}
    for c in claims:
        assert c["prop"] in props
        assert props[c["prop"]]["verdict"] in VERDICTS


# ------------------------------------------------------------------- (b) verbatim
def test_every_quote_is_verbatim(appdata):
    assert check_verbatim(appdata) == []


# --------------------------------------------------------------------- (c) enums
def test_required_top_level_keys(appdata):
    for key in ("meta", "stats", "nodes", "edges", "clusters"):
        assert key in appdata
    for key in ("documents", "doc_index", "chronology"):
        assert key in appdata


def test_appdata_enums_valid(appdata):
    assert check_enums(appdata) == []


def test_coherence_edges_run_bundle_to_pleading(appdata):
    """Direction invariant: coherence source is a non-pleading claim, target a pleading claim."""
    by_id = {n["id"]: n for n in appdata["nodes"]}
    for e in appdata["edges"]:
        if e["kind"] != "coherence":
            continue
        src, tgt = by_id.get(e["source"]), by_id.get(e["target"])
        assert src and tgt
        assert tgt.get("polarity") == "pleading"
        assert src.get("polarity") in ("bundle", "legal_overlay")


def test_overlays_in_vocabulary(appdata):
    for n in appdata["nodes"]:
        if n["layer"] == "proposition":
            assert n["overlay"] in OVERLAYS


# ------------------------------------------------------------------ (d) safety net
def test_assess_case_returns_every_proposition():
    props, bundle = _meridian()
    verdicts = api.assess_case(props, bundle, offline=True)
    for p in props:
        assert p["id"] in verdicts
        assert verdicts[p["id"]].verdict in VERDICTS
        assert 0.0 <= verdicts[p["id"]].confidence <= 1.0
    # synthesized propositions (02¶1/2/6/16 had no allegation) also resolve
    assert any(k.startswith("U02_") for k in verdicts)


def test_engine_verdict_shape_and_band():
    props, bundle = _meridian()
    verdicts = api.assess_case(props, bundle, offline=True)
    one = verdicts["P2"]
    assert isinstance(one.verdict, str) and isinstance(one.confidence, float)
    assert isinstance(one.verify, bool) and isinstance(one.evidence, list)
    assert one.overlay in OVERLAYS
    assert api.band(0.9) == "high"
    assert api.band(0.5) == "medium"
    assert api.band(0.1) == "low"


def test_safety_net_fires_on_single_source_fixture():
    props, bundle = synthetic_fixture()
    verdicts = api.assess_case(props, bundle, offline=True)
    assert verdicts["P1"].verify is True
    assert "single_source" in verdicts["P1"].note or verdicts["P1"].verify


def test_verify_marks_proposition_source_ai():
    props, bundle = synthetic_fixture()
    appdata = api.to_appdata(props, bundle, offline=True)
    prop = next(n for n in appdata["nodes"]
                if n["layer"] == "proposition" and n["label"] == "P1")
    assert prop["verify"] is True
    assert prop["source"] == "ai"
    safety.assert_coverage(appdata)


def test_offline_is_deterministic():
    props, bundle = _meridian()
    a = api.to_appdata(props, bundle, offline=True)
    b = api.to_appdata(props, bundle, offline=True)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
