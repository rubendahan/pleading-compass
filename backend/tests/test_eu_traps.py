"""Automated trap-proof harness for the treacherous EU case.

Proves the analysis engine catches OR correctly VERIFY-flags every planted trap, NEVER
marks a planted-unsupported claim as SUPPORTED at high confidence, and does NOT cry wolf
on a clean all-supported control.

The harness is GREEN today via the gold-as-engine oracle in ``src.engine_adapter`` and
switches to the real engine automatically when ``EU_TRAPS_ENGINE=engine_v2`` is set and
``engine_v2.api`` is importable (see ``src/engine_adapter.assess``). Every assertion is
written against the stable ``EngineVerdict`` surface, so it holds for either backing.
"""
from __future__ import annotations

import pytest

from data import clean_bundle_gold as C
from data import eu_traps_gold as T
from src import engine_adapter as EA
from src import numeric_check as NC


# --------------------------------------------------------------- fixtures / setup
PROPS, BUNDLE = T.compose()
GOLD = T.compose_gold()
RESULT = EA.assess(PROPS, BUNDLE, GOLD)          # {prop_id: EngineVerdict}

TRAP_IDS = list(T.TRAP_GOLD.keys())
_BAND_ORDER = {"low": 0, "medium": 1, "high": 2}


def _anchor_set(anchors) -> set:
    return {tuple(a) for a in anchors}


# ------------------------------------------------------------------- (a) verdicts
@pytest.mark.parametrize("pid", TRAP_IDS)
def test_trap_verdict_matches_or_verify_flagged(pid):
    """Engine verdict equals the gold verdict, OR — where gold permits human review —
    the engine raised VERIFY and landed on an honest non-committal verdict."""
    g = T.TRAP_GOLD[pid]
    r = RESULT[pid]
    ok = (
        r.verdict == g["verdict"]
        or (g["verify"] and r.verify
            and r.verdict in {g["verdict"], "UNVERIFIED", "NOT_ADDRESSED"})
    )
    assert ok, f"{pid}: got {r.verdict!r} (verify={r.verify}); gold {g['verdict']!r}"


# ----------------------------------------------- (b) THE HARD INVARIANT (no FP-high)
@pytest.mark.parametrize("pid", TRAP_IDS)
def test_trap_never_supported_high(pid):
    """A trap is never marked SUPPORTED at high confidence — the core failure to avoid."""
    r = RESULT[pid]
    assert not (r.verdict == "SUPPORTED" and EA.band(r.confidence) == "high"), \
        f"{pid}: planted trap returned SUPPORTED@high"


def test_no_unsupported_prop_is_supported_high_over_whole_bundle():
    """Property over the ENTIRE composed bundle (murky case + traps): every proposition
    whose gold verdict is not SUPPORTED must not come back SUPPORTED at high confidence."""
    offenders = [
        pid for pid, g in GOLD.items()
        if g["verdict"] != "SUPPORTED"
        and RESULT[pid].verdict == "SUPPORTED"
        and EA.band(RESULT[pid].confidence) == "high"
    ]
    assert offenders == [], f"SUPPORTED@high on non-SUPPORTED props: {offenders}"


# ----------------------------------------------------------------- (c) must_not
@pytest.mark.parametrize("pid", TRAP_IDS)
def test_trap_verdict_not_in_must_not(pid):
    g = T.TRAP_GOLD[pid]
    assert RESULT[pid].verdict not in g["must_not"], \
        f"{pid}: returned a forbidden verdict {RESULT[pid].verdict!r}"


# ------------------------------------------------------- (d) ambiguous -> UNVERIFIED
def test_ambiguous_trap_is_unverified_and_verify():
    """P20 (legacy 3DES; expert declines to opine) is genuinely ambiguous: the only
    honest answer is UNVERIFIED with the VERIFY flag set."""
    r = RESULT["P20"]
    assert r.verdict == "UNVERIFIED" and r.verify is True


# ---------------------------------------------- (e) decoy never cited without operative
@pytest.mark.parametrize("pid", ["P15", "P19"])
def test_decoy_not_cited_without_operative(pid):
    """If the engine surfaces a decoy anchor as evidence, it must also surface an
    operative anchor (the controlling document) — the decoy must never stand alone."""
    g = T.TRAP_GOLD[pid]
    ev = _anchor_set(RESULT[pid].evidence)
    decoys = _anchor_set(g["decoy_evidence"])
    operatives = _anchor_set(g["operative_evidence"])
    if ev & decoys:
        assert ev & operatives, \
            f"{pid}: decoy {ev & decoys} cited without any operative anchor"


# ------------------------------------------------------------- (f) cry-wolf guard
def test_clean_control_does_not_cry_wolf():
    """The all-supported control: every proposition SUPPORTED, no overlay, no VERIFY,
    and never a CONTRADICTED / NOT_ADDRESSED / UNVERIFIED false flag."""
    cprops, cbundle = C.compose()
    cgold = C.CLEAN_GOLD
    res = EA.assess(cprops, cbundle, cgold)
    for pid, g in cgold.items():
        r = res[pid]
        assert r.verdict == "SUPPORTED", f"{pid}: clean control flagged {r.verdict!r}"
        assert r.verify is False, f"{pid}: clean control asked for verification"
        assert r.overlay == "NONE", f"{pid}: clean control raised overlay {r.overlay!r}"
        for forbidden in g["must_not"]:
            assert r.verdict != forbidden


# ------------------------------------------------- (g) confidence band within one step
@pytest.mark.parametrize("pid", TRAP_IDS)
def test_confidence_band_within_one_step(pid):
    g = T.TRAP_GOLD[pid]
    got = _BAND_ORDER[EA.band(RESULT[pid].confidence)]
    want = _BAND_ORDER[g["confidence_band"]]
    assert abs(got - want) <= 1, \
        f"{pid}: band {EA.band(RESULT[pid].confidence)!r} vs gold {g['confidence_band']!r}"


# ------------------------------------------------------------- (h) verify-flag policy
@pytest.mark.parametrize("pid", TRAP_IDS)
def test_verify_flag_not_under_cautious(pid):
    """Over-caution is allowed (the engine may verify a crisp trap), but under-caution is
    not: whenever gold requires verification, the engine must raise VERIFY."""
    g = T.TRAP_GOLD[pid]
    if g["verify"]:
        assert RESULT[pid].verify is True, f"{pid}: gold needs VERIFY but engine did not flag"


# ------------------------------------------------------- (i) numeric trap (deterministic)
def test_numeric_trap_proven_disjoint():
    """P16's EUR 4.5m (30 days x daily gross revenue) vs the evidenced ~EUR 30k margin
    impact is proven CONTRADICTED by the deterministic numeric reconciler."""
    pairs = T.TRAP_GOLD["P16"]["numeric"]
    assert pairs, "P16 must carry a numeric pair for the solver"
    for spec in pairs:
        pd, pp = spec["pleaded_anchor"]
        ed, ep = spec["evidence_anchor"]
        pair = NC.DisputedPair(
            label=spec["label"], entity=spec["entity"], metric=spec["metric"],
            pleaded=spec["pleaded"], evidence=spec["evidence"],
            pleaded_anchor=f"{pd}¶{pp}", evidence_anchor=f"{ed}¶{ep}",
            tolerance=spec["tolerance"], unit=spec["unit"],
            legal_risk=T.TRAP_GOLD["P16"]["legal_risk"],
        )
        rec = NC.reconcile(pair)
        assert rec.status == "CONTRADICTED", \
            f"numeric pair {spec['label']} not proven disjoint: {rec.note}"


# ------------------------------------------------- (j) GOLD-INTEGRITY meta-test (no engine)
def test_gold_integrity_every_trap_has_gold():
    trap_ids = {tp["id"] for tp in T.TRAP_PROPOSITIONS}
    assert trap_ids == set(T.TRAP_GOLD), "trap propositions and TRAP_GOLD must align"


def test_gold_integrity_anchors_resolve():
    """Every operative / decoy anchor resolves to a real (doc, para) in the composed
    bundle — no claim ever points at a paragraph that does not exist."""
    for pid, g in T.TRAP_GOLD.items():
        for anchor in list(g["operative_evidence"]) + list(g["decoy_evidence"]):
            doc, para = anchor
            assert T.para_text(BUNDLE, doc, para) is not None, \
                f"{pid}: anchor {doc}¶{para} does not resolve in the bundle"


def test_gold_integrity_pleaded_paragraphs_resolve():
    """Each trap is pleaded at a paragraph that actually exists in the Particulars of
    Claim (doc 02 extended with the trap pleadings)."""
    for tp in T.TRAP_PROPOSITIONS:
        doc, para = tp["pleaded_at"]
        assert T.para_text(BUNDLE, doc, para) is not None, \
            f"{tp['id']}: pleaded anchor {doc}¶{para} does not resolve"


def test_gold_integrity_quotes_are_verbatim():
    """Every drafted quote is an EXACT substring of the paragraph it cites (the one hard
    rule the frontend's verify-highlighter depends on)."""
    for (doc, para), quote in T.QUOTES.items():
        text = T.para_text(BUNDLE, doc, para)
        assert text is not None, f"quote anchor {doc}¶{para} does not resolve"
        assert quote in text, f"non-verbatim quote at {doc}¶{para}: {quote!r}"


def test_gold_integrity_all_seven_trap_types_present():
    types = {g["trap_type"] for g in T.TRAP_GOLD.values()}
    assert len(types) == 7, f"expected 7 distinct trap types, got {sorted(types)}"
    assert types == set(T.TRAP_TYPES), f"trap types diverge from TRAP_TYPES: {sorted(types)}"


def test_gold_integrity_clean_control_quotes_are_verbatim():
    """The clean control's supporting quotes are verbatim too (positive control hygiene)."""
    _, cbundle = C.compose()
    for pid, g in C.CLEAN_GOLD.items():
        for doc, para in g["operative_evidence"]:
            text = T.para_text(cbundle, doc, para)
            assert text is not None and C.quote_for(pid) in text, \
                f"{pid}: clean support {doc}¶{para} not verbatim"
