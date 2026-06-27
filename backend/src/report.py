"""Reporting + practitioner views.

Turns judgements into what a litigator actually uses: a pleading-to-proof
matrix, per-issue trial-readiness, cross-examination points, gaps to fill,
and load-bearing (single-source) risks — all side-aware.
"""
from __future__ import annotations

import os
from typing import Optional

from .models import Judgement, Proposition

SUPPORTED = "🟢"
CONTRADICTED = "🔴"
NOT_ADDRESSED = "⚪"
UNVERIFIED = "❔"
_EMOJI = {"SUPPORTED": SUPPORTED, "CONTRADICTED": CONTRADICTED,
          "NOT_ADDRESSED": NOT_ADDRESSED, "UNVERIFIED": UNVERIFIED}
_SCORE = {"SUPPORTED": 1.0, "CONTRADICTED": 0.0, "NOT_ADDRESSED": 0.0, "UNVERIFIED": 0.5}


def emoji(verdict: str) -> str:
    return _EMOJI.get((verdict or "").upper(), UNVERIFIED)


def trial_readiness(judgements: list[Judgement], *, side: Optional[str] = None) -> dict:
    """Per-issue + overall readiness. With *side*, 'overall' covers only the
    propositions YOU must prove (burden == side)."""
    per = {j.proposition_id: round(100 * _SCORE.get(j.verdict, 0.0)) for j in judgements}
    scope = [j for j in judgements if side is None or j.burden == side]
    overall = round(100 * sum(_SCORE.get(j.verdict, 0.0) for j in scope) / len(scope)) if scope else 0
    return {"overall": overall, "per_issue": per}


def cross_exam_points(judgements, props_by_id, *, side: Optional[str] = None) -> list[dict]:
    """Opponent propositions that the evidence contradicts → cross-exam ammunition."""
    out = []
    for j in judgements:
        is_opponent = side is None or j.burden != side
        if not (is_opponent and j.verdict == "CONTRADICTED"):
            continue
        ev = next((e for e in j.evidence if e.polarity == "contradict"),
                  j.evidence[0] if j.evidence else None)
        if not ev:
            continue
        prop = props_by_id.get(j.proposition_id)
        out.append({
            "target_prop_id": j.proposition_id,
            "target_text": prop.text if prop else "",
            "put_to": ev.doc_id,
            "anchor": f"{ev.doc_id}¶{ev.para}",
            "quote": ev.quote,
            "note": j.contradictions[0].note if j.contradictions else "",
        })
    return out


def gaps_to_fill(judgements, props_by_id, *, side: Optional[str] = None) -> list[dict]:
    """YOUR propositions with no/insufficient proof → what to shore up."""
    out = []
    for j in judgements:
        is_yours = side is None or j.burden == side
        if not (is_yours and j.verdict in ("NOT_ADDRESSED", "UNVERIFIED")):
            continue
        prop = props_by_id.get(j.proposition_id)
        out.append({
            "prop_id": j.proposition_id,
            "prop_text": prop.text if prop else "",
            "missing": j.extra.get("note") or "No evidence in the bundle addresses this proposition.",
            "suggested_evidence": _suggest(prop),
        })
    return out


def load_bearing(judgements, props_by_id=None) -> list[dict]:
    """SUPPORTED propositions resting on a single source → single point of failure."""
    out = []
    for j in judgements:
        if not (j.verdict == "SUPPORTED" and j.single_source and j.evidence):
            continue
        e = j.evidence[0]
        prop = props_by_id.get(j.proposition_id) if props_by_id else None
        out.append({
            "prop_id": j.proposition_id,
            "prop_text": prop.text if prop else "",
            "doc_id": e.doc_id,
            "anchor": f"{e.doc_id}¶{e.para}",
            "risk": f"Rests on a single source ({e.doc_id}¶{e.para}); if that source is "
                    "discredited, the proposition collapses — consider corroboration.",
        })
    return out


def _suggest(prop: Optional[Proposition]) -> str:
    if not prop:
        return "Identify a witness or contemporaneous document on point."
    what = "defence" if prop.kind == "defence" else "allegation"
    return (f"Seek a witness statement or contemporaneous document establishing this {what}; "
            f"consider a targeted disclosure request or calling a witness who can speak to it.")


# ----------------------------------------------------------------- CLI render
_A = {"g": "\033[92m", "r": "\033[91m", "k": "\033[90m", "y": "\033[93m",
      "b": "\033[1m", "x": "\033[0m"}


def render_cli(result: dict) -> str:
    if os.name == "nt":
        os.system("")
    props = result.get("props", {})
    R = result["readiness"]
    out = [f"{_A['b']}CMS Pleading-to-Proof — case theory stress test{_A['x']}", "=" * 66]
    side = result.get("side") or "neutral"
    out.append(f"Acting for: {side}   ·   backend: {result.get('backend','')}   ·   "
               f"{_A['b']}trial-readiness {R['overall']}/100{_A['x']} (your burden)")
    out.append("")
    out.append(f"{_A['b']}Pleading-to-proof matrix{_A['x']}")
    for j in result["judgements"]:
        em = emoji(j["verdict"])
        pid = j["proposition_id"]
        text = (props.get(pid, {}).get("text", "") or "")[:88]
        per = R["per_issue"].get(pid, 0)
        lr = j.get("extra", {}).get("legal_risk")
        overlay = f"  {_A['y']}⚖ {lr}{_A['x']}" if lr else ""
        out.append(f"  {em} [{pid}] {j['verdict']:<13} ({per:>3}/100)  {text}{overlay}")
        for e in j["evidence"]:
            out.append(f"        ↳ {e['doc_id']}¶{e['para']} ({e['type']}, {e['weight']}): "
                       f"\"{_trunc(e['quote'], 90)}\"")
        if j.get("single_source") and j["verdict"] == "SUPPORTED":
            out.append(f"        {_A['y']}⚠ single source — load-bearing{_A['x']}")

    out += _section("Cross-examination points", [
        f"Put {p['anchor']} to {p['put_to']} → re [{p['target_prop_id']}] "
        f"\"{_trunc(p['target_text'], 60)}\"\n        evidence: \"{_trunc(p['quote'], 90)}\""
        for p in result.get("cross_exam", [])
    ])
    out += _section("Gaps to fill (your burden)", [
        f"[{g['prop_id']}] {_trunc(g['prop_text'], 70)}\n        missing: {g['missing']}"
        f"\n        → {g['suggested_evidence']}"
        for g in result.get("gaps", [])
    ])
    out += _section("Load-bearing evidence (single point of failure)", [
        f"[{lb['prop_id']}] {lb['anchor']} — {lb['risk']}" for lb in result.get("load_bearing", [])
    ])
    out += _section("Cross-document contradictions", [
        f"{c['ref_a']} ⟷ {c['ref_b']} — {c['note']}" for c in result.get("contradictions", [])
    ])
    return "\n".join(out)


def _section(title: str, lines: list[str]) -> list[str]:
    out = ["", f"{_A['b']}{title}{_A['x']}"]
    if not lines:
        out.append("  (none)")
    for ln in lines:
        out.append("  • " + ln)
    return out


def _trunc(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"


# ----------------------------------------------------------------- Markdown memo
def render_markdown(result: dict) -> str:
    props = result.get("props", {})
    R = result["readiness"]
    side = result.get("side") or "neutral"
    out = ["# Case theory stress test — analysis note", ""]
    out.append(f"**Acting for:** {side}  ·  **Trial-readiness (your burden):** {R['overall']}/100  ·  "
               f"backend: {result.get('backend','')}")
    out.append("")
    out.append("| Proposition | Verdict | Legal risk | Readiness | Evidence |")
    out.append("|---|---|---|---|---|")
    for j in result["judgements"]:
        pid = j["proposition_id"]
        ev = "; ".join(f"{e['doc_id']}¶{e['para']} ({e['weight']})" for e in j["evidence"]) or "—"
        lr = j.get("extra", {}).get("legal_risk") or "—"
        out.append(f"| {pid}: {_trunc(props.get(pid,{}).get('text',''),60)} | "
                   f"{emoji(j['verdict'])} {j['verdict']} | {lr} | {R['per_issue'].get(pid,0)}/100 | {ev} |")
    if result.get("cross_exam"):
        out += ["", "## Cross-examination points"]
        for p in result["cross_exam"]:
            out.append(f"- **Put {p['anchor']} to {p['put_to']}** — re {p['target_prop_id']}: "
                       f"\"{p['quote']}\"")
    if result.get("gaps"):
        out += ["", "## Gaps to fill (your burden)"]
        for g in result["gaps"]:
            out.append(f"- **{g['prop_id']}** — {g['missing']} → _{g['suggested_evidence']}_")
    if result.get("load_bearing"):
        out += ["", "## Load-bearing evidence"]
        for lb in result["load_bearing"]:
            out.append(f"- **{lb['prop_id']}** ({lb['anchor']}): {lb['risk']}")
    if result.get("contradictions"):
        out += ["", "## Cross-document contradictions"]
        for c in result["contradictions"]:
            out.append(f"- **{c['ref_a']} ⟷ {c['ref_b']}** — {c['note']}")
    return "\n".join(out)
