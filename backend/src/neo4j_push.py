"""Push all the engine's graphs to Neo4j when creds are set — ready for AuraDB.

Builds the Cypher for the coherence graph (evidence ↔ claims ↔ pleadings) and the EU
Acquis graph (acts + repeals→supersedes) and pushes both. Safe no-op without creds: it
prints the Cypher-emitted message instead. The evidence graph pushes via
``python -m src.cli --real --graph`` (it needs the loaded bundle).

    NEO4J_URI=neo4j+s://<id>.databases.neo4j.io NEO4J_PASSWORD=... python -m src.neo4j_push
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src import cellar, coherence, graph  # noqa: E402


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    jobs = {
        "coherence": coherence.coherence_to_cypher(coherence.analyse()),
        "eu_acquis": cellar.to_cypher(cellar.consolidate()),
    }
    for label, cypher in jobs.items():
        print(f"[{label}] {graph.push_cypher(cypher, label=label)}")
    print("[evidence] push via: python -m src.cli --real --graph   (needs the bundle + creds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
