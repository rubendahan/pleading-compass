"""Evidence graph — propositions <-> evidence <-> documents, with the litigation
queries that a matrix can't show as cleanly.

The same graph runs three ways, so the demo never depends on a live database:
  * **in-memory queries** (pure Python over the built graph) — always available;
  * **Cypher export** (``to_cypher``) — the real Neo4j artefact;
  * **push to Neo4j** (``push_to_neo4j``) — when ``NEO4J_URI`` + creds are set.

Signature queries (the reason this beats the flat matrix):
  * ``own_goal_contradictions`` — propositions contradicted by a document from the
    SAME side that pleaded them ("your own evidence sinks your own case");
  * ``unsupported_propositions`` — "absence as a query target": pleaded points with
    no incoming SUPPORTS edge;
  * ``load_bearing_sources`` — SUPPORTED points resting on a single document.
"""
from __future__ import annotations

import os
from typing import Optional


# --------------------------------------------------------------- graph builder
def build_graph(result: dict, bundle) -> dict:
    """Build ``{nodes, edges}`` from a ``pipeline.analyze`` result + the bundle.

    Nodes: Proposition, EvidenceItem, Document. Edges: SUPPORTS / CONTRADICTS
    (EvidenceItem -> Proposition) and QUOTED_FROM (EvidenceItem -> Document).
    """
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(node_id: str, kind: str, **attrs) -> str:
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "kind": kind, **attrs}
        return node_id

    props = result.get("props", {})
    for j in result.get("judgements", []):
        pid = j["proposition_id"]
        prop = props.get(pid, {})
        node(f"prop:{pid}", "Proposition", pid=pid, verdict=j.get("verdict", ""),
             party=prop.get("party", ""), burden=j.get("burden", ""),
             legal_risk=(j.get("extra") or {}).get("legal_risk", ""),
             text=prop.get("text", ""))
        for e in j.get("evidence", []):
            did = e["doc_id"]
            d = bundle.get(did)
            node(f"doc:{did}", "Document", doc_id=did,
                 title=(d.title if d else did), party=(d.party if d else "neutral"),
                 doc_type=(d.doc_type if d else "unknown"))
            ev_id = node(f"ev:{pid}:{did}:{e['para']}", "EvidenceItem", doc_id=did,
                         para=e["para"], polarity=e["polarity"], type=e["type"],
                         weight=e["weight"], quote=e["quote"])
            rel = "CONTRADICTS" if e["polarity"] == "contradict" else "SUPPORTS"
            edges.append({"source": ev_id, "target": f"prop:{pid}", "type": rel,
                          "weight": e["weight"]})
            edges.append({"source": ev_id, "target": f"doc:{did}", "type": "QUOTED_FROM",
                          "para": e["para"]})
    return {"nodes": list(nodes.values()), "edges": edges}


# --------------------------------------------------------------- signature queries
def own_goal_contradictions(result: dict, bundle) -> list[dict]:
    """Propositions contradicted by a document from the side that pleaded them."""
    props = result.get("props", {})
    out: list[dict] = []
    for j in result.get("judgements", []):
        if j.get("verdict") != "CONTRADICTED":
            continue
        party = props.get(j["proposition_id"], {}).get("party")
        for e in j.get("evidence", []):
            if e["polarity"] != "contradict":
                continue
            d = bundle.get(e["doc_id"])
            if d and party and d.party == party:
                out.append({"prop_id": j["proposition_id"], "doc_id": e["doc_id"],
                            "doc_title": d.title, "doc_type": d.doc_type,
                            "anchor": f"{e['doc_id']}¶{e['para']}", "quote": e["quote"]})
                break  # one own-goal source is enough to flag it
    return out


def unsupported_propositions(result: dict) -> list[dict]:
    """Absence as a query target: propositions with no incoming SUPPORTS edge."""
    out: list[dict] = []
    for j in result.get("judgements", []):
        if not any(e["polarity"] == "support" for e in j.get("evidence", [])):
            out.append({"prop_id": j["proposition_id"], "verdict": j.get("verdict", "")})
    return out


def load_bearing_sources(result: dict) -> list[dict]:
    """SUPPORTED propositions whose support rests on a single document."""
    out: list[dict] = []
    for j in result.get("judgements", []):
        if j.get("verdict") != "SUPPORTED":
            continue
        docs = {e["doc_id"] for e in j.get("evidence", []) if e["polarity"] == "support"}
        if len(docs) == 1:
            out.append({"prop_id": j["proposition_id"], "doc_id": next(iter(docs))})
    return out


# --------------------------------------------------------------- Cypher / Neo4j
def _cy(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return '""'
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{s}"'


def to_cypher(graph: dict) -> str:
    """Idempotent MERGE statements (one per line, ';'-terminated) for Neo4j."""
    lines = ["// Pleading-to-Proof evidence graph — run against a Neo4j database"]
    for n in graph["nodes"]:
        body = ", ".join(f"{k}: {_cy(v)}" for k, v in n.items() if k != "kind")
        lines.append(f'MERGE (n:{n["kind"]} {{id: {_cy(n["id"])}}}) SET n += {{{body}}};')
    for e in graph["edges"]:
        extra = {k: v for k, v in e.items() if k not in ("source", "target", "type")}
        setp = (" SET r += {" + ", ".join(f"{k}: {_cy(v)}" for k, v in extra.items()) + "}"
                if extra else "")
        lines.append(f'MATCH (a {{id: {_cy(e["source"])}}}), (b {{id: {_cy(e["target"])}}}) '
                     f'MERGE (a)-[r:{e["type"]}]->(b){setp};')
    return "\n".join(lines)


def push_to_neo4j(graph: dict, *, uri: Optional[str] = None, user: Optional[str] = None,
                  password: Optional[str] = None) -> str:
    """Push to Neo4j if creds are available; otherwise a no-op explaining how to enable.
    Reads ``NEO4J_URI`` / ``NEO4J_USER`` / ``NEO4J_PASSWORD`` from env by default."""
    uri = uri or os.getenv("NEO4J_URI")
    user = user or os.getenv("NEO4J_USER", "neo4j")
    password = password or os.getenv("NEO4J_PASSWORD")
    if not uri or not password:
        return "Neo4j not configured (set NEO4J_URI + NEO4J_PASSWORD) — Cypher emitted instead."
    try:
        from neo4j import GraphDatabase  # type: ignore
    except ImportError:
        return "neo4j driver not installed (pip install neo4j) — Cypher emitted instead."
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            for stmt in to_cypher(graph).split("\n"):
                stmt = stmt.strip().rstrip(";")
                if stmt and not stmt.startswith("//"):
                    session.run(stmt)
    finally:
        driver.close()
    return f"Pushed {len(graph['nodes'])} nodes / {len(graph['edges'])} edges to {uri}."


def push_cypher(cypher: str, *, uri: Optional[str] = None, user: Optional[str] = None,
                password: Optional[str] = None, label: str = "graph") -> str:
    """Run a ready Cypher string against Neo4j (for the coherence / EU graphs whose
    exporters already emit Cypher). Safe no-op without creds or driver."""
    uri = uri or os.getenv("NEO4J_URI")
    user = user or os.getenv("NEO4J_USER", "neo4j")
    password = password or os.getenv("NEO4J_PASSWORD")
    if not uri or not password:
        return "Neo4j not configured (set NEO4J_URI + NEO4J_PASSWORD) — Cypher emitted instead."
    try:
        from neo4j import GraphDatabase  # type: ignore
    except ImportError:
        return "neo4j driver not installed (pip install neo4j) — Cypher emitted instead."
    driver = GraphDatabase.driver(uri, auth=(user, password))
    n = 0
    try:
        with driver.session() as session:
            for stmt in cypher.split("\n"):
                stmt = stmt.strip().rstrip(";")
                if stmt and not stmt.startswith("//"):
                    session.run(stmt)
                    n += 1
    finally:
        driver.close()
    return f"Pushed {n} statements ({label}) to {uri}."


# --------------------------------------------------------------- CLI view
def render_graph_view(result: dict, bundle) -> str:
    g = build_graph(result, bundle)
    own = own_goal_contradictions(result, bundle)
    unsup = unsupported_propositions(result)
    lb = load_bearing_sources(result)
    out = [f"Evidence graph — {len(g['nodes'])} nodes, {len(g['edges'])} edges", ""]
    out.append("Own-goal contradictions (your own side's documents contradict your pleaded case):")
    for o in own:
        out.append(f"  • [{o['prop_id']}] contradicted by {o['anchor']} "
                   f"({o['doc_title']}, {o['doc_type']})")
    if not own:
        out.append("  (none)")
    out += ["", "Absence as a query target (no supporting evidence):"]
    out.append("  " + (", ".join(f"{u['prop_id']} [{u['verdict']}]" for u in unsup) or "(none)"))
    out += ["", "Load-bearing (rests on a single document):"]
    out.append("  " + (", ".join(f"{x['prop_id']} → {x['doc_id']}" for x in lb) or "(none)"))
    return "\n".join(out)
