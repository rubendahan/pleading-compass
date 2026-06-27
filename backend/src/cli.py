"""CLI:
    python -m src.cli                                  # self-test bundle, stub judge
    python -m src.cli --bundle data/bundle --judge longcontext --side claimant
    python -m src.cli --bakeoff                        # compare all available judges
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import answer_key, bakeoff, ingest, pipeline, pleadings, report
from .judges import get_judge

_DEFAULT_BUNDLE = str(Path(__file__).resolve().parents[1] / "data" / "selftest" / "bundle")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="src.cli",
                                 description="CMS Pleading-to-Proof — case theory stress test.")
    ap.add_argument("--bundle", default=_DEFAULT_BUNDLE, help="Folder of bundle documents.")
    ap.add_argument("--judge", default="stub", help="Judge name (stub|longcontext|rag|argument|numeric).")
    ap.add_argument("--side", default=None, choices=["claimant", "defendant"],
                    help="Whose case theory to stress-test (drives gaps vs cross-exam).")
    ap.add_argument("--stub", action="store_true", help="Force the offline stub backend.")
    ap.add_argument("--model", default=None, help="Override the LLM model.")
    ap.add_argument("--bakeoff", action="store_true", help="Run every available judge vs the GOLD answer key.")
    ap.add_argument("--real", action="store_true",
                    help="Use the real CMS bundle (data/bundle) + its draft answer key.")
    ap.add_argument("--graph", action="store_true",
                    help="Also build the evidence graph: signature queries + Cypher export (+ Neo4j push if configured).")
    ap.add_argument("--coverage", action="store_true",
                    help="For each NOT_ADDRESSED proposition, print the quantified search proof (queries run, paras inspected, best match vs threshold).")
    ap.add_argument("--semantic", action="store_true",
                    help="Use embedding cosine for coverage (Vertex AI if GOOGLE_CLOUD_PROJECT is set, else the local fallback) instead of lexical overlap.")
    ap.add_argument("--numeric", action="store_true",
                    help="Print the deterministic offline numeric reconciliation (z3): 40%% vs 6.2%%, £4.2m vs £1.3m, cl.14 cap.")
    ap.add_argument("--coherence", action="store_true",
                    help="Bundle-first paradigm: the strongest coherent story the bundle supports + which pleaded allegations it rejects (seeded POC).")
    ap.add_argument("--markdown", action="store_true", help="Emit the Markdown analysis note.")
    args = ap.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    key = answer_key.bundle_key() if args.real else None

    if args.bakeoff:
        rows = bakeoff.run_bakeoff(force_stub=args.stub, model=args.model, key=key)
        print(bakeoff.render_bakeoff(rows))
        return 0

    if key is not None:
        bundle = ingest.load_bundle(key.bundle_dir)
        props = key.propositions
    else:
        bundle = ingest.load_bundle(args.bundle)
        props = pleadings.extract_propositions(bundle, force_stub=args.stub, model=args.model)
    judge = get_judge(args.judge, force_stub=args.stub, model=args.model, key=key)

    def progress(i, total, label):
        print(f"  judging {i}/{total}: {label} ...", file=sys.stderr)

    result = pipeline.analyze(bundle, props, judge, side=args.side, progress=progress)
    print(f"[backend: {result['backend']}]", file=sys.stderr)
    print(report.render_markdown(result) if args.markdown else report.render_cli(result))

    if args.graph:
        from . import graph as graphmod
        g = graphmod.build_graph(result, bundle)
        cache = Path(__file__).resolve().parents[1] / "data" / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        cypher_path = cache / "evidence_graph.cypher"
        cypher_path.write_text(graphmod.to_cypher(g), encoding="utf-8")
        print("\n" + graphmod.render_graph_view(result, bundle))
        print(f"\n[cypher: {cypher_path}]", file=sys.stderr)
        print(f"[neo4j: {graphmod.push_to_neo4j(g)}]", file=sys.stderr)

    if args.coverage:
        from . import coverage
        embedder = None
        if args.semantic:
            from . import retrieval
            embedder = retrieval.get_embedder()
            print(f"[coverage: semantic embeddings via {type(embedder).__name__}]", file=sys.stderr)
        pleaded_at = key.pleaded_at if key is not None else {}
        print("\nCoverage of NOT_ADDRESSED propositions (is the absence real, or did we not look?):")
        gaps = [j for j in result["judgements"] if j["verdict"] == "NOT_ADDRESSED"]
        if not gaps:
            print("  (no NOT_ADDRESSED propositions on this case theory)")
        for j in gaps:
            pid = j["proposition_id"]
            prop = next((p for p in props if p.id == pid), None)
            if prop is None:
                continue
            own = pleaded_at.get(pid)
            exclude = {f"{own[0]}¶{own[1]}"} if own else set()
            rep = coverage.coverage_report(prop, bundle, exclude_anchors=exclude, embedder=embedder)
            print("  " + coverage.render_coverage(rep))

    if args.numeric:
        from . import numeric_check
        print("\n" + numeric_check.render(numeric_check.run_numeric_check()))

    if args.coherence:
        from . import coherence
        # Seeded from data/bundle_gold.py; quotes enrich when the real bundle is loaded.
        print("\n" + coherence.render_cli(coherence.analyse(bundle if args.real else None)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
