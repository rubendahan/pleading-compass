"""CLI:  python -m engine_v2.cli run --pleading <file> --bundle <dir> --out app.json [--offline] [--model ...]

Loads the evidence bundle from a directory, parses the pleading file, runs the
pipeline, writes the AppData JSON, and prints a short summary.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import ingest, pipeline


def _run(args) -> int:
    bundle = ingest.load_bundle(args.bundle) if args.bundle else ingest.Bundle()  # type: ignore[attr-defined]
    pleading = ingest.parse_doc(args.pleading)
    if not pleading.paras:
        print(f"error: no paragraphs parsed from {args.pleading}", file=sys.stderr)
        return 2
    # Ensure the pleading is in the bundle so documents[<tab>] exists for coverage.
    if bundle.get(pleading.id) is None:
        bundle.docs.append(pleading)
        bundle.docs.sort(key=lambda d: d.id)

    if args.model:
        os.environ["LLM_MODEL"] = args.model
    meta = {"case": args.case or pleading.title, "claim_no": args.claim_no or "",
            "court": args.court or "", "seeded": False}
    appdata = pipeline.to_appdata(pleading, bundle, offline=args.offline, meta=meta)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(appdata, fh, ensure_ascii=False, indent=2)

    props = [n for n in appdata["nodes"] if n["layer"] == "proposition"]
    verdicts: dict[str, int] = {}
    for n in props:
        verdicts[n["verdict"]] = verdicts.get(n["verdict"], 0) + 1
    print(f"wrote {args.out}: {len(props)} propositions, "
          f"{len(appdata['nodes'])} nodes, {len(appdata['edges'])} edges, "
          f"{len(appdata['clusters'])} clusters")
    print("  verdicts: " + ", ".join(f"{k}={v}" for k, v in sorted(verdicts.items())))
    print(f"  readiness={appdata['stats']['readiness']}/100  "
          f"own_goals={appdata['stats']['own_goal']}  "
          f"exposure={appdata['stats']['exposure_from']}→{appdata['stats']['exposure_to']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="engine_v2.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="analyze a pleading against a bundle")
    run.add_argument("--pleading", required=True, help="pleading file (.md/.txt/.docx/.pdf)")
    run.add_argument("--bundle", default="", help="directory of bundle documents")
    run.add_argument("--out", required=True, help="output app.json path")
    run.add_argument("--offline", action="store_true", help="force the deterministic stub")
    run.add_argument("--model", default="", help="override LLM model (when a key is set)")
    run.add_argument("--case", default="", help="case caption (meta.case)")
    run.add_argument("--claim-no", default="", help="claim number (meta.claim_no)")
    run.add_argument("--court", default="", help="court (meta.court)")
    run.set_defaults(func=_run)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # keep ¶/£/→ printable on Windows
    except Exception:
        pass
    raise SystemExit(main())
