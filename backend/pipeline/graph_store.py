"""Graph export and required Neo4j persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .config import Neo4jConfig
from .schemas import Claim, Edge, Evidence, GraphDocument, GraphNode


ALLOWED_NODE_LABELS = {"Claim", "Evidence"}
ALLOWED_EDGE_TYPES = {"USES_EVIDENCE", "SIMILAR_TO", "SUPPORTS", "CONTRADICTS"}


def build_graph_document(claims: list[Claim], evidence: list[Evidence]) -> GraphDocument:
    nodes: list[GraphNode] = []
    edges: list[Edge] = []
    evidence_ids = {item.id for item in evidence}

    for claim in claims:
        nodes.append(
            GraphNode(
                id=claim.id,
                labels=["Claim"],
                properties=claim.model_dump(),
            )
        )
        for evidence_id in claim.cited_evidence_ids:
            if evidence_id:
                normalized_id = evidence_id.upper()
                if normalized_id in evidence_ids:
                    edges.append(
                        Edge(
                            source_id=claim.id,
                            target_id=normalized_id,
                            type="USES_EVIDENCE",
                            rationale="Evidence id extracted from pleading claim.",
                        )
                    )

    for item in evidence:
        nodes.append(
            GraphNode(
                id=item.id,
                labels=["Evidence"],
                properties=item.model_dump(exclude={"raw_text"}),
            )
        )

    return GraphDocument(nodes=nodes, edges=edges)


def write_neo4j_graph(
    graph: GraphDocument,
    config: Neo4jConfig,
    *,
    warnings: list[str],
) -> None:
    driver = _build_neo4j_driver(config)
    try:
        driver.verify_connectivity()
        with driver.session(**_session_kwargs(config)) as session:
            session.execute_write(_write_graph_tx, graph)
    finally:
        driver.close()


def check_neo4j_connection(config: Neo4jConfig) -> None:
    driver = _build_neo4j_driver(config)
    try:
        driver.verify_connectivity()
    finally:
        driver.close()


def _build_neo4j_driver(config: Neo4jConfig):
    if not config.enabled:
        raise RuntimeError("Neo4j is required, but neo4j.enabled is false.")

    uri = os.getenv(config.uri_env)
    user = os.getenv(config.user_env)
    password = os.getenv(config.password_env)
    missing = [
        name
        for name, value in [
            (config.uri_env, uri),
            (config.user_env, user),
            (config.password_env, password),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Neo4j is required. Missing environment variable(s): "
            + ", ".join(missing)
        )

    try:
        from neo4j import GraphDatabase  # type: ignore
    except ModuleNotFoundError:
        raise RuntimeError("Neo4j is required. Install the `neo4j` package.")

    return GraphDatabase.driver(uri, auth=(user, password))


def _session_kwargs(config: Neo4jConfig) -> dict[str, str]:
    if config.database:
        return {"database": config.database}
    return {}


def _write_graph_tx(tx, graph: GraphDocument) -> None:  # pragma: no cover - needs Neo4j
    for node in graph.nodes:
        label = node.labels[0]
        if label not in ALLOWED_NODE_LABELS:
            raise ValueError(f"Unsupported Neo4j node label: {label}")
        tx.run(
            f"MERGE (n:{label} {{id: $id}}) SET n += $properties",
            id=node.id,
            properties=node.properties,
        )
    for edge in graph.edges:
        edge_type = edge.type
        if edge_type not in ALLOWED_EDGE_TYPES:
            raise ValueError(f"Unsupported Neo4j relationship type: {edge_type}")
        tx.run(
            f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            MERGE (source)-[r:{edge_type}]->(target)
            SET r += $properties
            """,
            source_id=edge.source_id,
            target_id=edge.target_id,
            properties=_neo4j_properties(
                edge.model_dump(
                    exclude={"source_id", "target_id", "type"},
                    exclude_none=True,
                )
            ),
        )


def _neo4j_properties(properties: dict) -> dict:
    """Convert nested metadata into Neo4j-safe property values."""

    converted = {}
    for key, value in properties.items():
        if isinstance(value, dict):
            converted[key] = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, list) and any(isinstance(item, dict) for item in value):
            converted[key] = json.dumps(value, ensure_ascii=False)
        else:
            converted[key] = value
    return converted


def ensure_output_dir(path: str | Path) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
