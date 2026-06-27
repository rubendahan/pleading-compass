"""EU Acquis coherence — the same engine, applied to real EU law via the Cellar API.

The EU Publications Office challenge (Acquis Management Programme) is about consolidating
EU legislation and detecting **gaps, overlaps, and contradictions** — which is exactly what
the coherence engine does. The cleanest, non-fabricated mapping uses real legal relations:

    act A repeals act B   ==>   A --supersedes--> B   (hard edge)

The deterministic ``coherence.solve_cluster`` then computes the maximum-weight consistent
set — the acts still **in force** (the consolidated Acquis) — and drops the superseded ones.
Repealing (current) acts are weighted above the acts they repeal, so chains and fan-outs
resolve the way a lawyer expects. The graph exports straight to Neo4j Cypher.

Data comes from the public **Cellar SPARQL endpoint** (open). The offline path uses a small
fixture of REAL repeals pairs cached from that endpoint, so tests run with no network; pass
``limit``/set creds to pull live.
"""
from __future__ import annotations

from typing import Optional

from .coherence import (CoherenceClaim, CoherenceCluster, CoherenceEdge,
                        CoherenceSolution, coherence_to_cypher, solve_cluster)

ENDPOINT = "http://publications.europa.eu/webapi/rdf/sparql"

_PREFIX = "PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>"
_REPEALS_Q = (
    _PREFIX + " SELECT ?ca ?cb WHERE { "
    "?a cdm:resource_legal_repeals_resource_legal ?b . "
    "?a cdm:resource_legal_id_celex ?ca . "
    "?b cdm:resource_legal_id_celex ?cb } LIMIT %d"
)

# Real repeals pairs (act CELEX, repealed-act CELEX) cached from the live Cellar endpoint —
# keeps the offline test deterministic and network-free.
SAMPLE_REPEALS: list[tuple[str, str]] = [
    ("31992R2333", "31985R3309"),
    ("32013R0576", "32004R1994"),
    ("32014R0559", "32011R1183"),
]


def sparql(query: str, *, timeout: int = 30) -> list[dict]:
    """Run a SPARQL query against the Cellar endpoint, return bindings as plain dicts."""
    import requests
    resp = requests.get(ENDPOINT,
                        params={"query": query, "format": "application/sparql-results+json"},
                        timeout=timeout)
    resp.raise_for_status()
    return [{k: v["value"] for k, v in b.items()}
            for b in resp.json()["results"]["bindings"]]


def fetch_repeals(limit: int = 50) -> list[tuple[str, str]]:
    """Live: (act, repealed-act) CELEX pairs from Cellar."""
    return [(r["ca"], r["cb"]) for r in sparql(_REPEALS_Q % int(limit))]


def build_cluster(repeals: list[tuple[str, str]]) -> CoherenceCluster:
    """One claim per EU act; each `repeals` becomes a hard `supersedes` edge. A repealing
    (current) act outweighs the act it repeals, so the superseded ones are dropped."""
    repealers = {a for a, _ in repeals}
    acts = sorted({c for pair in repeals for c in pair})
    claims = [
        CoherenceClaim(
            id=celex, issue="EU_ACQUIS", text=f"EU legal act {celex}",
            proposition_id=None, source_doc=celex, source_para=None, quote=None,
            source_type="eu_act", weight=(2.0 if celex in repealers else 1.0),
            polarity="bundle",
        )
        for celex in acts
    ]
    edges = [CoherenceEdge(a, b, "supersedes", True, f"{a} repeals {b}", "eu_repeals")
             for a, b in repeals]
    return CoherenceCluster(issue="EU_ACQUIS", claims=claims, edges=edges,
                            meta={"story": [], "amendments": [], "gold": {}})


def consolidate(repeals: Optional[list[tuple[str, str]]] = None) -> CoherenceSolution:
    """Solve for the in-force (consolidated) set. Uses the live fetch if *repeals* is None
    and the endpoint is reachable, else the cached real-data fixture."""
    if repeals is None:
        try:
            repeals = fetch_repeals()
        except Exception:
            repeals = SAMPLE_REPEALS
    return solve_cluster(build_cluster(repeals))


def to_cypher(solution: CoherenceSolution) -> str:
    """Neo4j Cypher for the EU acts graph (Claim nodes + SUPERSEDES), reusing the
    coherence exporter."""
    return coherence_to_cypher([solution])
