"""Evidence-graph builder + signature queries + Cypher export.

Runs on the self-test bundle (always present), so it needs no API key and no
real CMS data. The self-test deliberately contains a defence proposition (D2)
that is contradicted by a same-side (defendant) witness — an 'own goal'.
"""
from __future__ import annotations

from src import graph
from src.ingest import load_bundle
from src.judges.stub import judge
from src.pipeline import analyze
from src.pleadings import seed_propositions

BUNDLE = "data/selftest/bundle"


def _result():
    b = load_bundle(BUNDLE)
    return analyze(b, seed_propositions(), judge, side="claimant"), b


def test_graph_has_the_three_node_kinds_and_quoted_from():
    res, b = _result()
    g = graph.build_graph(res, b)
    kinds = {n["kind"] for n in g["nodes"]}
    assert {"Proposition", "EvidenceItem", "Document"} <= kinds
    rels = {e["type"] for e in g["edges"]}
    assert {"QUOTED_FROM"} <= rels and ("SUPPORTS" in rels or "CONTRADICTS" in rels)


def test_own_goal_query_flags_same_side_contradiction():
    res, b = _result()
    own = {o["prop_id"] for o in graph.own_goal_contradictions(res, b)}
    # D2 (defendant defence) is contradicted by doc 04, a defendant witness statement
    assert "D2" in own


def test_absence_as_a_query_target():
    res, b = _result()
    unsup = {u["prop_id"] for u in graph.unsupported_propositions(res)}
    assert {"P3", "G1"} <= unsup          # the two NOT_ADDRESSED gaps have no support


def test_cypher_export_is_well_formed():
    res, b = _result()
    cy = graph.to_cypher(graph.build_graph(res, b))
    assert "MERGE (n:Proposition" in cy
    assert "QUOTED_FROM" in cy and "CONTRADICTS" in cy
    assert cy.strip().endswith(";")          # every statement terminated


def test_neo4j_push_is_a_safe_noop_without_config(monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    res, b = _result()
    msg = graph.push_to_neo4j(graph.build_graph(res, b))
    assert "not configured" in msg.lower()


def test_push_cypher_is_a_safe_noop_without_config(monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    assert "not configured" in graph.push_cypher("MERGE (n:X {id: 1});").lower()
