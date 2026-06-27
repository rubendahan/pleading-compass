"""Calibration + the VERIFY flag + the hard coverage invariant.

Confidence is blended in [0, 1] from: the top-K support similarity, the distinct-
source count (single-source penalty), the support/contradict agreement entropy
(ported from ``src/confidence.py``), the LLM self-confidence, and a hard zero if a
required quote is not verbatim. VERIFY is raised whenever the result is fragile:
low confidence, single source, weak/ambiguous support, an empty/low LLM signal,
or a NOT_ADDRESSED near-miss.

`assert_coverage` is the load-bearing invariant: every paragraph of the pleading
(documents["02"]) must resolve to a pleading claim AND a proposition carrying a
non-empty verdict — so the "02¶6 has no status" bug is unreachable.
"""
from __future__ import annotations

import math

from .models import VERDICTS

VERIFY_THRESHOLD = 0.55


# ----------------------------------------------- ported agreement math (confidence.py)
def _vote_distribution(verdicts: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for v in verdicts:
        counts[v] = counts.get(v, 0) + 1
    return counts


def normalized_entropy(verdicts: list[str]) -> float:
    n = len(verdicts)
    if n <= 1:
        return 0.0
    counts = list(_vote_distribution(verdicts).values())
    k = len(counts)
    if k <= 1:
        return 0.0
    h = 0.0
    for c in counts:
        p = c / n
        h -= p * math.log(p)
    return min(1.0, max(0.0, h / math.log(k)))


def margin(verdicts: list[str]) -> float:
    n = len(verdicts)
    if n == 0:
        return 0.0
    counts = sorted(_vote_distribution(verdicts).values(), reverse=True)
    top = counts[0] / n
    second = counts[1] / n if len(counts) > 1 else 0.0
    return top - second


def panel_confidence(verdicts: list[str]) -> float:
    if not verdicts:
        return 0.0
    conf = 0.5 * (1.0 - normalized_entropy(verdicts)) + 0.5 * margin(verdicts)
    return min(1.0, max(0.0, conf))


# ------------------------------------------------------------------ calibration
def calibrate(*, verdict: str, best_support: float, votes: list[str],
              distinct_sources: int, llm_self_conf: float | None,
              quote_verbatim: bool, coverage_max: float = 0.0,
              decisive: bool = False) -> float:
    """Blend the signals into a single calibrated confidence in [0, 1].

    The blend is *mode-aware*: it averages only the signals that actually exist.
    Offline there are no panel votes and no LLM self-confidence, so those terms
    must not silently drag every result below threshold (the old cry-wolf bug);
    we re-normalise over the available weights instead. A ``decisive`` hard
    contradiction (a fired deterministic surfacer) is treated as high-signal.
    """
    if not quote_verbatim and verdict in ("SUPPORTED", "CONTRADICTED"):
        return 0.0                                    # hard zero: unverifiable quote

    if verdict == "SUPPORTED":
        signal = best_support
    elif verdict == "CONTRADICTED":
        signal = 0.85 if decisive else max(best_support, 0.55)
    elif verdict == "NOT_ADDRESSED":
        signal = 1.0 - min(1.0, coverage_max)         # confident only if nothing matched
    else:  # UNVERIFIED
        signal = 0.4 * max(best_support, 0.3)

    weighted = [(0.6, signal)]                        # the support/contradiction signal
    if votes:
        weighted.append((0.25, panel_confidence(votes)))
    if llm_self_conf is not None:
        weighted.append((0.2, max(0.0, min(1.0, llm_self_conf))))
    wsum = sum(w for w, _ in weighted)
    conf = sum(w * v for w, v in weighted) / wsum
    if distinct_sources <= 1 and verdict == "SUPPORTED":
        conf *= 0.85                                  # single-source penalty (support only)
    return round(min(1.0, max(0.0, conf)), 4)


def verify_flags(*, verdict: str, confidence: float, single_source: bool,
                 best_support: float, ambiguous: bool, llm_low: bool,
                 coverage_max: float = 0.0,
                 threshold: float = 0.55) -> tuple[bool, list[str]]:
    """Decide the VERIFY flag and record why (the reasons feed the UI/spec)."""
    reasons: list[str] = []
    # NOT_ADDRESSED / UNVERIFIED are inherently "the lawyer must act" (a gap to
    # source, or genuinely unclear) — always flag them, never silently.
    if verdict in ("NOT_ADDRESSED", "UNVERIFIED"):
        reasons.append("evidential_gap" if verdict == "NOT_ADDRESSED" else "unverified")
        if verdict == "NOT_ADDRESSED" and coverage_max >= (threshold - 0.1):
            reasons.append("not_addressed_near_miss")
        return True, reasons
    # SUPPORTED / CONTRADICTED: only flag when the finding is actually fragile,
    # so a clean multi-source support or a decisive contradiction is NOT cried over.
    if confidence < VERIFY_THRESHOLD:
        reasons.append("low_confidence")
    if verdict == "SUPPORTED" and single_source:
        reasons.append("single_source")
    if verdict == "SUPPORTED" and best_support < threshold:
        reasons.append("weak_support")
    if ambiguous:
        reasons.append("ambiguous_support")
    if llm_low:
        reasons.append("low_llm_signal")
    return (len(reasons) > 0), reasons


# -------------------------------------------------------------- the invariant
def _pleading_tab(appdata: dict) -> str:
    """The tab the pleading sits at — derived from where pleading claims anchor.

    Most reliable signal (and JSON-only, for re-loaded outputs): the tab that the
    ``polarity:"pleading"`` claims point at. Falls back to a claimant pleading
    document, then to ``"02"``.
    """
    counts: dict[str, int] = {}
    for n in appdata.get("nodes", []):
        if n.get("layer") == "claim" and n.get("polarity") == "pleading":
            anchor = n.get("anchor") or ""
            tab = anchor.split("¶", 1)[0]
            if tab:
                counts[tab] = counts.get(tab, 0) + 1
    if counts:
        return max(counts, key=lambda t: (counts[t], t))
    docs = appdata.get("documents", {}) or {}
    if "02" in docs:
        return "02"
    for tab, d in docs.items():
        if (d or {}).get("doc_type") == "pleading" and (d or {}).get("party") == "claimant":
            return tab
    return "02"


def assert_coverage(appdata: dict) -> None:
    """Hard invariant: every pleading paragraph resolves to a claim + a verdict.

    Raises ``AssertionError`` if any paragraph of the pleading tab lacks a
    pleading claim anchored at it OR a resolvable proposition with a non-empty,
    valid verdict. This is what guarantees ``02¶6`` (and every other paragraph)
    always carries a status.
    """
    tab = _pleading_tab(appdata)
    docs = appdata.get("documents", {}) or {}
    pleading = docs.get(tab)
    assert pleading is not None, f"coverage: no documents['{tab}'] (the pleading)"

    nodes = appdata.get("nodes", [])
    props = {n["id"]: n for n in nodes if n.get("layer") == "proposition"}
    pleading_claims: dict[int, list[dict]] = {}
    for n in nodes:
        if n.get("layer") == "claim" and n.get("polarity") == "pleading":
            anchor = n.get("anchor") or ""
            if anchor.startswith(f"{tab}¶"):
                try:
                    para = int(anchor.split("¶", 1)[1])
                except (ValueError, IndexError):
                    continue
                pleading_claims.setdefault(para, []).append(n)

    for para in pleading.get("paras", []):
        n = para["n"]
        claims = pleading_claims.get(n, [])
        assert claims, f"coverage: {tab}¶{n} has no pleading claim"
        ok = False
        for c in claims:
            prop = props.get(f"prop:{c.get('prop')}")
            if prop and prop.get("verdict") in VERDICTS:
                ok = True
                break
        assert ok, f"coverage: {tab}¶{n} has no resolvable proposition with a verdict"
