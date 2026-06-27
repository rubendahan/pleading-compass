"""Tests for the A1 (`hackthelaw`) -> AppData bridge (``a1_bridge.py``).

A real A1 phase-2 run needs Vertex/OpenAI auth, so these run against a committed
synthetic fixture under ``tests/fixtures/a1_run`` + ``tests/fixtures/a1_case``
that matches ``hackthelaw/schemas.py`` (3 claims, 5 evidence, one clearly
contradicting document). The fixture exercises the full mapping and every
front-end invariant in ``demo/BACKEND-OUTPUT-SPEC.md``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import a1_bridge

FIX = Path(__file__).parent / "fixtures"
RUN = FIX / "a1_run"
CASE = FIX / "a1_case"

VERDICTS = {"SUPPORTED", "CONTRADICTED", "NOT_ADDRESSED", "UNVERIFIED"}
OVERLAYS = {"NONE", "CONTRACTUALLY_BARRED", "SUPERSEDED", "CAPPED",
            "CAUSATION_PROBLEM", "BURDEN_PROBLEM"}
EDGE_KINDS = {"provenance", "coherence", "impact"}
EDGE_RELS = {"asserts", "contradicts", "supersedes", "supports", "caps",
             "qualifies", "attacks", "legal_bar", "belongs_to"}


@pytest.fixture(scope="module")
def app() -> dict:
    return a1_bridge.build_appdata(RUN, CASE)


def _nodes(app, layer):
    return [n for n in app["nodes"] if n.get("layer") == layer]


def _node(app, nid):
    for n in app["nodes"]:
        if n["id"] == nid:
            return n
    return None


def _para_text(app, tab, para):
    doc = app["documents"].get(tab)
    if not doc:
        return None
    for p in doc["paras"]:
        if p["n"] == para:
            return p["text"]
    return None


# ------------------------------------------------------------- top-level shape
def test_required_keys_present(app):
    # Five required + the documents/doc_index/chronology overlays we keep.
    for key in ("meta", "stats", "nodes", "edges", "clusters",
                "documents", "doc_index", "chronology"):
        assert key in app, f"missing top-level key {key}"
    # sensitivity is intentionally the only sacrifice.
    assert "sensitivity" not in app


def test_meta_from_manifest(app):
    m = app["meta"]
    assert m["case"] == "Meridian Retail Group plc v TechFlow Solutions Limited"
    assert m["claim_no"] == "HT-2025-000999"
    assert m["court"] == "Technology and Construction Court"


def test_meta_override():
    app = a1_bridge.build_appdata(RUN, CASE, meta={"case": "Override v Test", "seeded": False})
    assert app["meta"]["case"] == "Override v Test"
    assert app["meta"]["seeded"] is False


def test_stats(app):
    s = app["stats"]
    assert 0 <= s["readiness"] <= 100
    assert s["props"] == len(_nodes(app, "proposition"))
    assert s["docs"] == len(_nodes(app, "document"))
    assert s["claims"] == len(_nodes(app, "claim"))
    assert s["rejected_pleadings"] == 2          # C002 + C003 are not SUPPORTED
    assert isinstance(s["exposure_from"], str) and isinstance(s["exposure_to"], str)
    assert s["exposure_from"] == "£6.0m"          # max pleaded figure


# ----------------------------------------------------------------- node ids
def test_node_id_prefixes(app):
    for n in app["nodes"]:
        layer = n["layer"]
        prefix = {"proposition": "prop:", "claim": "claim:", "document": "doc:"}[layer]
        assert n["id"].startswith(prefix), f"{n['id']} wrong prefix for {layer}"
    # doc node id == tab id
    for d in _nodes(app, "document"):
        assert d["id"] == f"doc:{d['label']}"


def test_proposition_enums_and_spread(app):
    props = _nodes(app, "proposition")
    assert len(props) == 3
    verdicts = {p["label"]: p["verdict"] for p in props}
    for p in props:
        assert p["verdict"] in VERDICTS
        assert p["overlay"] in OVERLAYS
        assert p["overlay"] == "NONE"            # A1 has no overlays
        assert 0 <= p["readiness"] <= 100
        assert isinstance(p["text"], str) and p["text"]
    # the full mapping spread is exercised
    assert verdicts["P1"] == "SUPPORTED"
    assert verdicts["P2"] == "CONTRADICTED"
    assert verdicts["P3"] == "NOT_ADDRESSED"


def test_at_least_one_contradicted(app):
    contradicted = [p for p in _nodes(app, "proposition") if p["verdict"] == "CONTRADICTED"]
    assert contradicted, "expected at least one CONTRADICTED proposition from challenging evidence"


# --------------------------------------------------- the hard verbatim rule
def test_every_claim_quote_is_verbatim(app):
    """The one hard rule: every claim.quote is a literal substring of the exact
    paragraph it anchors to (documents[tab].paras[para].text)."""
    claims = _nodes(app, "claim")
    assert claims
    for c in claims:
        anchor, quote = c.get("anchor"), c.get("quote")
        if anchor is None and quote is None:
            continue                              # absence claim (allowed)
        assert "¶" in anchor, f"anchor {anchor!r} not in <tab>¶<para> form"
        tab, _, para = anchor.partition("¶")
        assert para.isdigit(), f"anchor {anchor!r} para is not an int"
        text = _para_text(app, tab, int(para))
        assert text is not None, f"anchor {anchor!r} does not resolve to a real (tab,para)"
        assert quote in text, f"quote for {c['id']} is NOT a verbatim substring of {anchor}"


def test_pleading_claims_anchor_tab_02(app):
    for c in _nodes(app, "claim"):
        if c.get("polarity") == "pleading":
            assert c["anchor"].startswith("02¶"), "pleading claims must sit at tab 02"
            assert c["prop"] and not c["prop"].startswith("prop:")  # bare label


# ---------------------------------------------------------------- edges
def test_edge_enums(app):
    for e in app["edges"]:
        assert e["kind"] in EDGE_KINDS
        assert e["rel"] in EDGE_RELS
        assert _node(app, e["source"]) is not None, f"dangling source {e['source']}"
        assert _node(app, e["target"]) is not None, f"dangling target {e['target']}"


def test_coherence_edges_run_bundle_to_pleading(app):
    coherence = [e for e in app["edges"] if e["kind"] == "coherence"]
    assert coherence
    for e in coherence:
        src, tgt = _node(app, e["source"]), _node(app, e["target"])
        assert src["polarity"] == "bundle", "coherence source must be a bundle claim"
        assert tgt["polarity"] == "pleading", "coherence target must be a pleading claim"


def test_contradiction_is_a_hard_coherence_edge(app):
    """The CONTRADICTED proposition's pleading claim is the target of a hard
    `contradicts` coherence edge from a bundle claim."""
    p2_claim = "claim:C002"
    hard = [e for e in app["edges"]
            if e["kind"] == "coherence" and e["target"] == p2_claim
            and e["rel"] == "contradicts" and e.get("hard")]
    assert hard, "expected a hard contradicts edge into the contradicted pleading claim"


def test_impact_edges_pleading_to_prop(app):
    impact = [e for e in app["edges"] if e["kind"] == "impact"]
    assert impact
    for e in impact:
        assert e["rel"] == "belongs_to"
        assert _node(app, e["source"])["polarity"] == "pleading"
        assert _node(app, e["target"])["layer"] == "proposition"
        assert e["verdict"] in ("accepted", "rejected")


def test_provenance_edges_doc_to_bundle_claim(app):
    prov = [e for e in app["edges"] if e["kind"] == "provenance"]
    assert prov
    for e in prov:
        assert e["source"].startswith("doc:")
        assert _node(app, e["target"])["polarity"] == "bundle"
        assert e["rel"] == "asserts"


# ---------------------------------------------------------- documents / index
def test_documents_cover_whole_bundle_with_full_paras(app):
    docs = app["documents"]
    # pleading + every evidence tab (5 evidence in the fixture)
    assert set(docs.keys()) == {"02", "03", "07", "08", "09", "19"}
    for tab, d in docs.items():
        assert d["paras"], f"documents[{tab}] has no paragraphs"
        for p in d["paras"]:
            assert isinstance(p["n"], int) and isinstance(p["text"], str) and p["text"]
        assert d["doc_type"] in {"contract", "pleading", "witness", "expert",
                                 "record", "correspondence"}
        assert d["party"] in {"claimant", "defendant", "neutral"}
    assert docs["02"]["doc_type"] == "pleading"
    assert docs["02"]["party"] == "claimant"


def test_doc_index_covers_all_bundle_tabs(app):
    di = app["doc_index"]
    assert di, "doc_index must be non-empty"
    index_tabs = {d["tab"] for d in di}
    assert index_tabs == set(app["documents"].keys()), "doc_index must cover every documents tab"
    # sorted by tab
    assert [d["tab"] for d in di] == sorted(d["tab"] for d in di)
    for d in di:
        assert d["party"] in {"claimant", "defendant", "neutral"}
        assert "title" in d and "category" in d


def test_chronology_present_sorted_and_anchored(app):
    chrono = app["chronology"]
    assert chrono, "chronology must be non-empty"
    dates = [c["date"] for c in chrono]
    assert dates == sorted(dates), "chronology must be ascending by date"
    for i, c in enumerate(chrono, start=1):
        assert c["n"] == i
        assert c["event"]
        assert c["source"] == "ai"
        for ev in c["evidence"]:
            assert ev["tab"] in app["documents"], f"chronology tab {ev['tab']} not in documents"
            if ev["para"] is not None:
                assert _para_text(app, ev["tab"], ev["para"]) is not None


# ---------------------------------------------------------------- clusters
def test_clusters_join_on_issue(app):
    cluster_issues = {c["issue"] for c in app["clusters"]}
    claim_issues = {n["issue"] for n in _nodes(app, "claim")}
    assert claim_issues <= cluster_issues, "every claim issue must have a matching cluster"
    for c in app["clusters"]:
        assert isinstance(c["story"], list)
        assert isinstance(c["amendments"], list)
        # each impacts line starts with the proposition label + colon
        for line in c["impacts"]:
            assert line.startswith(c["issue"] + ":"), f"impacts line must start '{c['issue']}: '"


def test_contradicted_cluster_has_amendments(app):
    p2 = next(c for c in app["clusters"] if c["issue"] == "P2")
    assert p2["amendments"], "the contradicted issue should carry lawyer-facing fixes"
