"""Deterministic, offline numeric reconciliation — the "Z3 angle" headline.

Where ``src/judges/numeric.py`` asks an LLM to *extract* well-typed facts and
then feeds them to a solver, this module is its deterministic complement: it
hard-codes the case's three disputed headline quantities (each still anchored to
a real paragraph of the bundle) and PROVES the contradictions with z3 every time
the demo runs — no API key, no model, no network. The solver, not the prose,
decides.

The three disputed quantities in *Meridian Retail Group plc v TechFlow Solutions
Ltd* (Claim HT-2025-000231):

1. Platform unavailability — the Particulars of Claim plead the Platform was
   unavailable for >40% of trading hours (P5, pleaded at 02¶11); the IT expert
   puts Platform-attributable unavailability at ~6.2% (19¶3).  40% vs 6.2%.
2. Loss of profit — pleaded £4,200,000 (P9b, 02¶15); the quantum expert supports
   only ~£1,300,000 (20¶4).  £4.2m vs £1.3m.
3. Damages cap — claimed total = wasted expenditure £1,800,000 (P9a) + loss of
   profit £4,200,000 (P9b) = £6,000,000; MSA clause 14 (03¶14) excludes loss of
   profit and caps liability near £1,800,000.  Recoverable £1.8m, not £6.0m.

Mechanism.  For each disputed pair we introduce one shared ``z3.Real`` and pin
it to BOTH the pleaded figure and the evidenced figure, each within the stated
tolerance band.  If the two tolerance bands are disjoint the conjunction is
UNSAT — a proof, citing BOTH anchors, that the figures cannot describe the same
quantity → ``CONTRADICTED``.  Compatible figures stay SAT → ``CONSISTENT``.

Graceful degradation.  ``import z3`` is guarded inside the solving function; if
z3 is unavailable (or ``use_z3=False``) an arithmetically identical pure-Python
*interval* check runs instead: the intervals ``[pleaded±tol]`` and
``[evidence±tol]`` are disjoint ⇔ the bands cannot overlap ⇔ CONTRADICTED.  Both
paths return the SAME verdict — that equivalence is the point, and it keeps the
check meaningful even in z3-less CI.
"""
from __future__ import annotations

from dataclasses import dataclass

from .judges.base import make_anchor


# --------------------------------------------------------------- data shapes
@dataclass(frozen=True)
class DisputedPair:
    """An anchored pleaded-vs-evidence numeric pair to reconcile."""
    label: str
    entity: str
    metric: str
    pleaded: float
    evidence: float
    pleaded_anchor: str
    evidence_anchor: str
    tolerance: float
    unit: str = ""
    legal_risk: str = "NONE"


@dataclass
class Reconciliation:
    """The solver's verdict on one disputed pair (the demo's output unit)."""
    label: str
    entity: str
    metric: str
    pleaded: float
    evidence: float
    pleaded_anchor: str
    evidence_anchor: str
    tolerance: float
    status: str            # "CONTRADICTED" | "CONSISTENT"
    solver: str            # "z3" | "interval"
    note: str
    unit: str = ""
    legal_risk: str = "NONE"


# --------------------------------------------------------------- the dataset
# Each pleaded figure is anchored where it is pleaded in the Particulars of Claim
# (doc 02); each evidenced figure to the expert report / contract that rebuts it.
AVAILABILITY = DisputedPair(
    label="platform_unavailability",
    entity="Platform",
    metric="unavailability (% of trading hours)",
    pleaded=40.0,                          # P5: ">40%"
    evidence=6.2,                          # IT expert: ~6.2% Platform-attributable
    pleaded_anchor=make_anchor("02", 11),
    evidence_anchor=make_anchor("19", 3),
    tolerance=0.5,                         # percentage points
    unit="%",
    legal_risk="CAUSATION_PROBLEM",
)

LOSS_OF_PROFIT = DisputedPair(
    label="loss_of_profit",
    entity="Meridian peak-period trading",
    metric="loss of profit",
    pleaded=4_200_000.0,                   # P9b
    evidence=1_300_000.0,                  # quantum expert (supportable)
    pleaded_anchor=make_anchor("02", 15),
    evidence_anchor=make_anchor("20", 4),
    tolerance=50_000.0,
    unit="GBP",
    legal_risk="CAPPED",
)

DAMAGES_CAP = DisputedPair(
    label="damages_cap",
    entity="recoverable damages",
    metric="total liability exposure",
    pleaded=6_000_000.0,                   # claimed total = 1.8m wasted + 4.2m profit
    evidence=1_800_000.0,                  # MSA cl.14 cap
    pleaded_anchor=make_anchor("02", 15),
    evidence_anchor=make_anchor("03", 14),
    tolerance=50_000.0,
    unit="GBP",
    legal_risk="CAPPED",
)

# A genuinely *consistent* pair: the pleaded wasted expenditure is accepted by the
# quantum expert. Shows the solver confirms what the evidence supports, not only
# what it contradicts — the same machinery, the opposite verdict.
WASTED_EXPENDITURE = DisputedPair(
    label="wasted_expenditure",
    entity="Meridian wasted expenditure",
    metric="sums paid under the MSA",
    pleaded=1_800_000.0,                   # P9a
    evidence=1_800_000.0,                  # quantum expert accepts ~£1.8m
    pleaded_anchor=make_anchor("02", 15),
    evidence_anchor=make_anchor("20", 2),
    tolerance=50_000.0,
    unit="GBP",
    legal_risk="CAPPED",
)

DISPUTED_PAIRS: list[DisputedPair] = [
    AVAILABILITY, LOSS_OF_PROFIT, DAMAGES_CAP, WASTED_EXPENDITURE,
]

# Cap figures, surfaced both as a Reconciliation (above) and as explicit math.
_CLAIMED_WASTED = 1_800_000
_CLAIMED_PROFIT = 4_200_000
_CAP = 1_800_000


# --------------------------------------------------------------- helpers
def _fmt(value: float, unit: str) -> str:
    """Figure for display: ``40%`` / ``6.2%`` for percentages, ``£4,200,000`` for GBP."""
    if unit == "%":
        return f"{value:g}%"
    if unit == "GBP":
        return f"£{value:,.0f}"
    return f"{value:g}"


def _bands_disjoint(claim: DisputedPair) -> bool:
    """Pure-python equivalent of the solver: True iff ``[pleaded±tol]`` and
    ``[evidence±tol]`` do not overlap."""
    lo_p, hi_p = claim.pleaded - claim.tolerance, claim.pleaded + claim.tolerance
    lo_e, hi_e = claim.evidence - claim.tolerance, claim.evidence + claim.tolerance
    return hi_p < lo_e or hi_e < lo_p


def _z3_disjoint(claim: DisputedPair, z3) -> bool:
    """One shared ``Real`` pinned (within tolerance) to BOTH figures; UNSAT iff the
    tolerance bands cannot overlap — the contradiction the solver proves."""
    x = z3.Real(claim.label)
    solver = z3.Solver()
    solver.add(x >= claim.pleaded - claim.tolerance, x <= claim.pleaded + claim.tolerance)
    solver.add(x >= claim.evidence - claim.tolerance, x <= claim.evidence + claim.tolerance)
    return solver.check() == z3.unsat


def _note(claim: DisputedPair, status: str, solver: str) -> str:
    p = f"{_fmt(claim.pleaded, claim.unit)} ({claim.pleaded_anchor})"
    e = f"{_fmt(claim.evidence, claim.unit)} ({claim.evidence_anchor})"
    if status == "CONTRADICTED":
        return (f"Incompatible {claim.metric} for '{claim.entity}': pleaded {p} vs "
                f"evidence {e}; the {solver} solver proved the tolerance bands "
                f"disjoint (UNSAT) — legal risk {claim.legal_risk}.")
    return (f"Reconcilable {claim.metric} for '{claim.entity}': pleaded {p} and "
            f"evidence {e} agree within ±{_fmt(claim.tolerance, claim.unit)} ({solver}).")


# --------------------------------------------------------------- public API
def reconcile(claim: DisputedPair, *, use_z3: bool = True) -> Reconciliation:
    """Reconcile one disputed pair, preferring z3 and degrading to intervals.

    With z3 available and ``use_z3`` set, a single ``Real`` is pinned to both the
    pleaded and the evidenced figure (each within ``tolerance``); an UNSAT
    conjunction → ``CONTRADICTED``. Otherwise the arithmetically identical
    interval check runs (``solver="interval"``). Both paths agree by construction.
    """
    solver = "interval"
    if use_z3:
        try:
            import z3
        except ImportError:
            z3 = None
        if z3 is not None:
            disjoint = _z3_disjoint(claim, z3)
            solver = "z3"
        else:
            disjoint = _bands_disjoint(claim)
    else:
        disjoint = _bands_disjoint(claim)

    status = "CONTRADICTED" if disjoint else "CONSISTENT"
    return Reconciliation(
        label=claim.label, entity=claim.entity, metric=claim.metric,
        pleaded=claim.pleaded, evidence=claim.evidence,
        pleaded_anchor=claim.pleaded_anchor, evidence_anchor=claim.evidence_anchor,
        tolerance=claim.tolerance, status=status, solver=solver,
        note=_note(claim, status, solver), unit=claim.unit, legal_risk=claim.legal_risk,
    )


def cap_analysis() -> dict:
    """The damages cap as explicit arithmetic: MSA cl.14 excludes loss of profit
    and caps liability near £1.8m, so ``recoverable = min(claimed_total, cap)``."""
    claimed_total = _CLAIMED_WASTED + _CLAIMED_PROFIT      # 6,000,000
    recoverable = min(claimed_total, _CAP)                 # 1,800,000
    cap_anchor = make_anchor("03", 14)
    return {
        "wasted_expenditure": _CLAIMED_WASTED,
        "loss_of_profit": _CLAIMED_PROFIT,
        "excluded_loss_of_profit": _CLAIMED_PROFIT,
        "claimed_total": claimed_total,
        "cap": _CAP,
        "recoverable": recoverable,
        "pleaded_anchor": make_anchor("02", 15),
        "cap_anchor": cap_anchor,
        "note": (f"MSA cl.14 ({cap_anchor}) excludes loss of profit and caps liability "
                 f"near £{_CAP:,.0f}: claimed £{claimed_total:,.0f} "
                 f"(£{_CLAIMED_WASTED:,.0f} wasted + £{_CLAIMED_PROFIT:,.0f} profit) "
                 f"→ recoverable £{recoverable:,.0f}."),
    }


def run_numeric_check(*, use_z3: bool = True) -> list[Reconciliation]:
    """Reconcile every disputed pair in the dataset (deterministic, fully offline)."""
    return [reconcile(pair, use_z3=use_z3) for pair in DISPUTED_PAIRS]


def render(reconciliations: list[Reconciliation]) -> str:
    """Plain-text, anchored summary — e.g. a line reads
    ``40% (02¶11) vs 6.2% (19¶3) → CONTRADICTED [z3]``."""
    title = "Deterministic numeric reconciliation (offline) — the solver, not the prose, decides"
    out = [title, "=" * len(title)]
    width = max((len(r.label) for r in reconciliations), default=0)
    for r in reconciliations:
        p = f"{_fmt(r.pleaded, r.unit)} ({r.pleaded_anchor})"
        e = f"{_fmt(r.evidence, r.unit)} ({r.evidence_anchor})"
        risk = f"   [risk: {r.legal_risk}]" if r.legal_risk and r.legal_risk != "NONE" else ""
        out.append(f"  {r.label:<{width}}  {p} vs {e} → {r.status} [{r.solver}]{risk}")
    cap = cap_analysis()
    out.append("")
    out.append(f"  cap: claimed £{cap['claimed_total']:,.0f} → recoverable "
               f"£{cap['recoverable']:,.0f} (MSA cl.14 excludes loss of profit; cap ≈ £1.8m)")
    return "\n".join(out)


if __name__ == "__main__":   # pragma: no cover - convenience demo entry point
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # keep ¶/£/→ printable on Windows
    except Exception:
        pass
    print(render(run_numeric_check()))
    print()
    print(cap_analysis()["note"])
