"""EU Acquis coherence over real Cellar data (the EU Publications Office / Neo4j angle).

The SAME coherence engine, applied to EU law: an act that REPEALS another is a `supersedes`
edge, so the deterministic solver computes which acts are still in force (the consolidated
Acquis) — the EU analogue of "which pleaded allegations survive". The offline test runs on a
fixture of REAL repeals pairs cached from the live Cellar SPARQL endpoint; the live fetch is
exercised only when CELLAR_LIVE=1 (network).
"""
from __future__ import annotations

import os

import pytest

from src import cellar


def test_consolidation_rejects_repealed_acts_keeps_repealers():
    sol = cellar.consolidate(cellar.SAMPLE_REPEALS)
    rejected = {c.id for c in sol.rejected}
    accepted = {c.id for c in sol.accepted}
    # repealed acts are no longer in force
    assert {"31985R3309", "32004R1994", "32011R1183"} <= rejected
    # the repealing (current) acts survive
    assert {"31992R2333", "32013R0576", "32014R0559"} <= accepted


def test_eu_graph_exports_cypher_with_supersedes():
    cy = cellar.to_cypher(cellar.consolidate(cellar.SAMPLE_REPEALS))
    assert "MERGE (n:Claim" in cy
    assert "SUPERSEDES" in cy
    assert cy.strip().endswith(";")


@pytest.mark.skipif(os.getenv("CELLAR_LIVE") != "1", reason="hits the live Cellar endpoint")
def test_fetch_repeals_live():
    rows = cellar.fetch_repeals(limit=3)
    assert rows and all(len(p) == 2 and p[0] and p[1] for p in rows)
