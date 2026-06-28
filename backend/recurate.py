"""Re-curation layer: raw mapper AppData  ->  the shipped Meridian demo.

`mapper.py` gives full coverage of the backend run (every pleaded point flagged,
the rich per-claim analysis carried in `clusters`). But the raw output drops three
things the product's philosophy depends on, because the run artefacts don't carry
them:

  * own-goals -- `evidence.json` has no `party`, so the mapper can't tell which
    contradicting evidence is the *claimant's own*. We re-attach `party` per tab
    and re-mark `own_goal` on contradicting/superseding edges sourced from a
    claimant document. Own-goals are the signature feature (header "own goals X/10").
  * real PDFs -- the mapper emits no `file_url`. We re-attach `/sources/NN.pdf`
    for every tab that has a PDF in `public/sources`; tabs without one keep the
    in-context paragraph reader (verbatim-quote highlighting), which the mapper
    already supports for all 19 docs.
  * the case caption -- the run manifest orders it defendant-first; we restore the
    correct "Meridian (claimant) v TechFlow (defendant)" caption.

Deterministic; reads only the mapper output + the `public` dir. It does not touch
the verdicts, quotes, anchors, or the cluster analysis the mapper produced.

CLI::

    python recurate.py --in raw.json --out ../src/lib/demo-case.json --public ../public
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Meridian = Claimant, TechFlow = Defendant (see cases/cms_synthetic/bundle_index.md).
# Party per litigation tab. Anything not listed is neutral (bilateral contracts,
# shared records, correspondence).
CLAIMANT_TABS = {"02", "12", "14", "16", "17", "18", "19", "20"}
DEFENDANT_TABS = {"15"}

# Contradiction-type relations: a claimant-sourced one of these is an own-goal.
OWN_GOAL_RELS = {"contradicts", "supersedes", "attacks"}

META = {
    "case": "Meridian Retail Group plc  v  TechFlow Solutions Ltd",
    "claim_no": "HT-2025-000231",
    "court": "Technology and Construction Court",
    "seeded": False,
}


def tab_of(node: dict) -> str | None:
    """The litigation tab a node belongs to: doc label, or a claim's anchor tab."""
    if node.get("layer") == "document":
        return node.get("label") or (node.get("id", "").split(":")[-1] or None)
    anchor = node.get("anchor")
    if anchor:
        m = re.match(r"^([0-9A-Za-z]+)", str(anchor))
        if m:
            return m.group(1)
    return None


def party_for(tab: str | None) -> str:
    if tab in CLAIMANT_TABS:
        return "claimant"
    if tab in DEFENDANT_TABS:
        return "defendant"
    return "neutral"


def recurate(app: dict, public_dir: Path) -> dict:
    # 1) caption
    app["meta"] = {**app.get("meta", {}), **META}

    # 2) party per tab -> documents map + document nodes
    for tab, doc in (app.get("documents") or {}).items():
        doc["party"] = party_for(tab)
    nodes_by_id = {n["id"]: n for n in app["nodes"]}
    for n in app["nodes"]:
        if n.get("layer") == "document":
            n["party"] = party_for(tab_of(n))

    # 3) own-goals. An own-goal is a pleaded point the claimant's OWN bundle defeats:
    # a DECISIVE (hard) contradiction from a claimant document, into a point that
    # actually falls (proposition verdict CONTRADICTED). We flag each such edge (the
    # graph / EdgeView read `own_goal` per edge) and the headline stat counts the
    # DISTINCT pleaded points -- the lawyer-facing number. Non-decisive contrary
    # evidence from one's own side is not promoted to an own-goal.
    own_points: set[str] = set()
    for e in app["edges"]:
        src = nodes_by_id.get(e.get("source") if isinstance(e.get("source"), str) else None)
        tgt = nodes_by_id.get(e.get("target") if isinstance(e.get("target"), str) else None)
        prop = (
            nodes_by_id.get(f"prop:{tgt.get('prop')}")
            if tgt is not None and tgt.get("layer") == "claim" and tgt.get("prop")
            else None
        )
        is_own = bool(
            e.get("rel") in OWN_GOAL_RELS
            and e.get("hard")
            and src is not None
            and src.get("layer") == "claim"
            and party_for(tab_of(src)) == "claimant"
            and prop is not None
            and prop.get("verdict") == "CONTRADICTED"
        )
        e["own_goal"] = is_own
        if is_own:
            own_points.add(tgt.get("prop") or tgt.get("id"))
    app.setdefault("stats", {})["own_goal"] = len(own_points)

    # 4) re-attach real PDFs where we have them; others keep the paragraph reader
    src_dir = public_dir / "sources"
    for tab, doc in (app.get("documents") or {}).items():
        pdf = src_dir / f"{tab}.pdf"
        if pdf.exists():
            doc["file_url"] = f"/sources/{tab}.pdf"
            doc["mime"] = "application/pdf"
        else:
            doc["file_url"] = None  # -> SourceReader falls back to the paragraph reader

    return app


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", required=True, help="raw mapper AppData json")
    ap.add_argument("--out", required=True, help="re-curated AppData json (the demo)")
    ap.add_argument("--public", required=True, help="frontend public/ dir (for /sources)")
    args = ap.parse_args(argv)

    app = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    app = recurate(app, Path(args.public))
    Path(args.out).write_text(
        json.dumps(app, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    s = app["stats"]
    print(
        f"Wrote {args.out}: own_goals={s.get('own_goal')}, props={s.get('props')}, "
        f"docs={s.get('docs')}, claims={s.get('claims')}, readiness={s.get('readiness')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
