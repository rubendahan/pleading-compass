"""Ensemble panel judge (brick #3b) — one calibrated verdict from many judges.

Instead of a bake-off where each judge is read separately, the panel runs
several independent judges over the same proposition and combines their votes
into ONE ``Judgement`` whose *confidence is calibrated by agreement*: when the
members agree the panel is confident, when they disagree that disagreement IS
the uncertainty signal (normalised entropy / vote margin, via ``confidence``).
This is the trustworthy-AI / Luminance-style angle — the system surfaces where
it is unsure rather than bluffing a single answer.

The winning verdict is the deterministic plurality (``confidence.plurality_verdict``);
the aggregated evidence/contradictions are taken from the winner-aligned members
only, deduplicated; and ``extra`` carries the full vote breakdown plus the list
of dissenting members. Offline (``force_stub`` / no API key) every member defers
to the deterministic stub, so the panel is unanimous and reproducible.
"""
from __future__ import annotations

from typing import Callable, Optional, Union

from . import base, stub
from .. import confidence
from ..models import Contradiction, EvidenceItem, Judgement, Proposition, Bundle

# Default member judges. NEVER includes "panel" (no recursion) and not "stub"
# (offline every member defers to the stub anyway, so the panel stays unanimous).
DEFAULT_MEMBERS: list[str] = ["longcontext", "rag", "argument", "numeric"]

# A member is either a registry name (resolved lazily via get_judge) or a ready
# judge callable injected directly (the testable seam for dissent scenarios).
Member = Union[str, base.JudgeFn]


def _resolve_members(members: list[Member], *, force_stub: bool,
                     model: Optional[str], key) -> list[base.JudgeFn]:
    """Turn the member spec into concrete judge callables. Names go through a
    LAZILY-imported ``get_judge`` (panel lives inside the ``judges`` package, so
    importing the registry at module load would be a cycle); already-callable
    members pass through untouched. Members that fail to construct are skipped."""
    from . import get_judge  # lazy: avoids judges/__init__ <-> panel import cycle

    resolved: list[base.JudgeFn] = []
    for m in members:
        if callable(m):
            resolved.append(m)
        elif isinstance(m, str):
            try:
                resolved.append(get_judge(m, force_stub=force_stub, model=model, key=key))
            except Exception:
                continue  # unknown/unimportable member judge — skip it
    return resolved


def _dedupe_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """Dedupe by (doc_id, para, polarity), keeping first-seen order."""
    seen: set[tuple[str, int, str]] = set()
    out: list[EvidenceItem] = []
    for e in items:
        ek = (e.doc_id, e.para, e.polarity)
        if ek in seen:
            continue
        seen.add(ek)
        out.append(e)
    return out


def _dedupe_contradictions(items: list[Contradiction]) -> list[Contradiction]:
    """Dedupe by (ref_a, ref_b), keeping first-seen order."""
    seen: set[tuple[str, str]] = set()
    out: list[Contradiction] = []
    for c in items:
        ck = (c.ref_a, c.ref_b)
        if ck in seen:
            continue
        seen.add(ck)
        out.append(c)
    return out


def make_judge(*, force_stub: bool = False, model: Optional[str] = None, key=None,
               members: Optional[list[Member]] = None) -> base.JudgeFn:
    """Return an ensemble ``judge(proposition, bundle)`` closure.

    ``members`` is a list of registry names (e.g. ``"rag"``) and/or judge
    callables; it defaults to :data:`DEFAULT_MEMBERS`. Names are resolved via a
    lazily-imported ``get_judge(name, force_stub=..., model=..., key=...)`` and
    any that fail to construct are skipped. If no member can be constructed the
    panel falls back to the deterministic stub bound to *key* so it never
    hard-fails.
    """
    if members is None:
        members = list(DEFAULT_MEMBERS)
    member_fns = _resolve_members(members, force_stub=force_stub, model=model, key=key)
    fallback = stub.make_judge(key=key)

    def _judge(proposition: Proposition, bundle: Bundle) -> Judgement:
        judgements: list[Judgement] = []
        for fn in member_fns:
            try:
                judgements.append(fn(proposition, bundle))
            except Exception:
                continue  # a member that blows up does not sink the panel
        if not judgements:
            return fallback(proposition, bundle)  # never hard-fail

        verdicts = [j.verdict for j in judgements]
        winner = confidence.plurality_verdict(verdicts)
        aligned = [j for j in judgements if j.verdict == winner]

        evidence = _dedupe_evidence([e for j in aligned for e in j.evidence])
        contradictions = _dedupe_contradictions([c for j in aligned for c in j.contradictions])

        extra = {
            "votes": confidence.vote_distribution(verdicts),
            "entropy": confidence.normalized_entropy(verdicts),
            "margin": confidence.margin(verdicts),
            "label": confidence.agreement_label(verdicts),
            "members": [(j.backend, j.verdict, j.confidence) for j in judgements],
            "dissent": [(j.backend, j.verdict) for j in judgements if j.verdict != winner],
        }
        return Judgement(
            proposition.id, winner, confidence.panel_confidence(verdicts),
            evidence, contradictions,
            single_source=base.is_single_source(evidence),
            burden=proposition.burden,
            backend=f"panel({len(judgements)})",
            extra=extra,
        )

    return _judge


def judge(proposition: Proposition, bundle: Bundle) -> Judgement:
    """Module-level convenience judge with the default member binding."""
    return make_judge()(proposition, bundle)
