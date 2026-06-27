"""Re-load an app.json and assert the hard guarantees hold.

Checks: (1) coverage — every pleading paragraph (incl. 02¶6) has a status;
(2) every quote is a verbatim substring of its cited paragraph; (3) every enum
value is valid; (4) the safety net fires on a synthetic single-source fixture
(verify=True and proposition.source=="ai").

Usage:  python -m engine_v2.verify_output [app.json]
        (no path → only the synthetic safety-net check runs)
"""
from __future__ import annotations

import json
import sys

from . import api, safety
from .models import OVERLAYS, RELATIONS, VERDICTS

_LAYERS = {"document", "claim", "proposition"}
_CLAIM_VERDICTS = {"accepted", "rejected"}
_POLARITY = {"pleading", "bundle", "legal_overlay"}
_KINDS = {"provenance", "coherence", "impact"}


def check_verbatim(appdata: dict) -> list[str]:
    docs = appdata.get("documents", {}) or {}
    bad: list[str] = []
    for n in appdata.get("nodes", []):
        if n.get("layer") != "claim":
            continue
        anchor, quote = n.get("anchor"), n.get("quote")
        if not anchor or not quote:
            continue
        tab, _, para = anchor.partition("¶")
        doc = docs.get(tab)
        if not doc:
            continue
        para_text = next((p["text"] for p in doc.get("paras", []) if str(p["n"]) == para), None)
        if para_text is None or quote not in para_text:
            bad.append(f"{n['id']} quote not verbatim at {anchor}")
    return bad


def check_enums(appdata: dict) -> list[str]:
    errs: list[str] = []
    for n in appdata.get("nodes", []):
        layer = n.get("layer")
        if layer not in _LAYERS:
            errs.append(f"bad layer {layer!r} on {n.get('id')}")
        if layer == "proposition":
            if n.get("verdict") not in VERDICTS:
                errs.append(f"bad prop verdict {n.get('verdict')!r} on {n.get('id')}")
            if n.get("overlay") not in OVERLAYS:
                errs.append(f"bad overlay {n.get('overlay')!r} on {n.get('id')}")
        if layer == "claim":
            if n.get("verdict") not in _CLAIM_VERDICTS:
                errs.append(f"bad claim verdict {n.get('verdict')!r} on {n.get('id')}")
            if n.get("polarity") not in _POLARITY:
                errs.append(f"bad polarity {n.get('polarity')!r} on {n.get('id')}")
    for e in appdata.get("edges", []):
        if e.get("kind") not in _KINDS:
            errs.append(f"bad edge kind {e.get('kind')!r}")
        if e.get("rel") not in RELATIONS:
            errs.append(f"bad edge rel {e.get('rel')!r}")
    return errs


def synthetic_fixture() -> tuple[list, dict]:
    """A single-source, high-match fixture — verify must fire (single_source)."""
    propositions = [{
        "id": "P1",
        "text": "The platform was unavailable for more than 40% of trading hours.",
        "pleaded_at": ("02", 1),
    }]
    bundle = {
        "02": {"doc_type": "pleading", "party": "claimant", "title": "Particulars",
               "paras": [(1, "The platform was unavailable for more than 40% of trading hours.")]},
        "05": {"doc_type": "record", "party": "neutral", "title": "Ops log",
               "paras": [(1, "Platform unavailability reached more than 40% of trading hours in the period.")]},
    }
    return propositions, bundle


def check_safety_net() -> list[str]:
    errs: list[str] = []
    props, bundle = synthetic_fixture()
    verdicts = api.assess_case(props, bundle, offline=True)
    ev = verdicts.get("P1")
    if ev is None or not ev.verify:
        errs.append("safety net: verify did not fire on the single-source fixture")
    appdata = api.to_appdata(props, bundle, offline=True)
    prop = next((n for n in appdata["nodes"]
                 if n["layer"] == "proposition" and n["label"] == "P1"), None)
    if prop is None or prop.get("source") != "ai":
        errs.append("safety net: proposition.source != 'ai' when verify is set")
    return errs


def verify_file(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as fh:
        appdata = json.load(fh)
    errs: list[str] = []
    try:
        safety.assert_coverage(appdata)
    except AssertionError as exc:
        errs.append(f"coverage: {exc}")
    errs.extend(check_verbatim(appdata))
    errs.extend(check_enums(appdata))
    return errs


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    errs: list[str] = []
    if argv:
        errs.extend(verify_file(argv[0]))
    errs.extend(check_safety_net())
    if errs:
        print("FAIL:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("OK: coverage, verbatim quotes, enums, and the safety net all hold.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
