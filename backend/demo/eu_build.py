"""Export the EU Acquis coherence graph as data_eu.json — data contract for the frontend.

Runs the same engine over real EU law (Cellar `repeals` → `supersedes`) and emits a graph
of acts coloured by whether the solver keeps them in force (accepted) or finds them
superseded (rejected). Pulls live from Cellar when reachable, else the cached fixture.

Run:  python demo/eu_build.py   ->   writes demo/data_eu.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_DEMO = Path(__file__).resolve().parent
_ROOT = _DEMO.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src import cellar  # noqa: E402


def build_data(limit: int = 60) -> dict:
    try:
        repeals = cellar.fetch_repeals(limit=limit)
        live = True
    except Exception:
        repeals, live = cellar.SAMPLE_REPEALS, False

    sol = cellar.consolidate(repeals)
    accepted = {c.id for c in sol.accepted}
    repealers = {a for a, _ in repeals}

    nodes = [{
        "id": c.id, "label": c.id, "layer": "act",
        "verdict": "accepted" if c.id in accepted else "rejected",
        "in_force": c.id in accepted,
        "is_repealer": c.id in repealers,
        "weight": c.weight,
    } for c in (sol.accepted + sol.rejected)]
    edges = [{"source": e.source, "target": e.target, "rel": "supersedes",
              "explanation": e.explanation} for e in sol.edges]

    return {
        "meta": {"source": "EU Cellar SPARQL (publications.europa.eu)",
                 "relation": "repeals → supersedes",
                 "challenge": "EU Publications Office — Acquis consolidation",
                 "live": live},
        "stats": {"acts": len(nodes), "in_force": len(sol.accepted),
                  "superseded": len(sol.rejected), "relations": len(edges)},
        "nodes": nodes,
        "edges": edges,
    }


def main() -> int:
    data = build_data()
    (_DEMO / "data_eu.json").write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    print(f"wrote {_DEMO / 'data_eu.json'}  "
          f"({data['stats']['acts']} acts, {data['stats']['in_force']} in force, "
          f"{data['stats']['superseded']} superseded, live={data['meta']['live']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
