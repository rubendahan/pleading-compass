"""General contradiction detection — NO case recipes.

Deterministic surfacers that work on ANY pleading/bundle:
  * numeric-disjoint   — comparable magnitudes (%, £) that cannot reconcile;
  * date-inconsistency — a supersession/variation that moves a pleaded date;
  * supersession       — "revised / varied / change order" + a date;
  * contractual cap / allocation — caps, exclusions, responsibility re-allocation;
  * semantic-negation  — the pleading denies what contemporaneous material affirms.

Plus one generic LLM classifier (strict tool use) that NAMES the mechanism and
returns the coherence relation. Offline (no key) → the deterministic surfacers
only. Direction is always BUNDLE → PLEADING.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .lexical import similarity, tokens
from .llm import LLM, MODEL_EXTRACT

REL_NONE = "none"
_HARD = {"contradicts", "supersedes"}


@dataclass
class Finding:
    rel: str                # contradicts | supersedes | supports | caps | qualifies | attacks | legal_bar | none
    hard: bool = False
    mechanism: str = ""
    explanation: str = ""
    own_goal: bool = False
    deterministic: bool = False   # True = a precise surfacer fired (trust it); False = LLM guess

    @property
    def is_contradiction(self) -> bool:
        return self.rel in ("contradicts", "supersedes", "caps", "qualifies",
                            "attacks", "legal_bar")


# ------------------------------------------------------------- number helpers
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_GBP = re.compile(r"(?:£|gbp\s*)\s*([\d,]+(?:\.\d+)?)", re.I)


def _nums(rx, text: str) -> list[float]:
    out = []
    for m in rx.finditer(text or ""):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return out


def _numeric_disjoint(claim: str, ev: str) -> Finding | None:
    for rx, unit, rel_tol in ((_PCT, "%", 0.4), (_GBP, "£", 0.4)):
        cs, es = _nums(rx, claim), _nums(rx, ev)
        if not cs or not es:
            continue
        cmax, emax = max(cs), max(es)
        if cmax <= 0 or emax <= 0:
            continue
        gap = abs(cmax - emax) / max(cmax, emax)
        if gap >= rel_tol:
            return Finding(
                rel="contradicts", hard=True, mechanism="numeric-disjoint",
                explanation=(f"Pleaded {cmax:g}{unit} vs evidenced {emax:g}{unit} — "
                             f"the figures cannot describe the same quantity."),
            )
    return None


_SUPERSEDE_KW = ("revised", "varied", "variation", "change order", "superseded",
                 "amended", "deed of variation", "revises")
_DATE = re.compile(r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b")


def _supersession(claim: str, ev: str) -> Finding | None:
    low = (ev or "").lower()
    if any(k in low for k in _SUPERSEDE_KW) and _DATE.search(ev or ""):
        return Finding(
            rel="supersedes", hard=True, mechanism="supersession",
            explanation="A signed variation re-states the term the pleading relies on.",
        )
    return None


_CAP_KW = ("cap", "capped", "shall not exceed", "limited to", "excludes loss",
           "exclude loss", "limit of liability", "liability cap")
_BAR_KW = ("entire agreement", "non-reliance", "no reliance", "responsibility of",
           "shall be responsible", "is responsible for", "own staff")


def _contractual(claim: str, ev: str) -> Finding | None:
    low = (ev or "").lower()
    if any(k in low for k in _CAP_KW):
        return Finding(rel="caps", hard=False, mechanism="contractual-cap",
                       explanation="A contractual cap/exclusion limits the pleaded sum.")
    if any(k in low for k in _BAR_KW):
        return Finding(rel="legal_bar", hard=False, mechanism="contractual-allocation",
                       explanation="A contract clause re-allocates the duty the pleading asserts.")
    return None


_NEG = ("did not", "do not", "does not", "no ", "not ", "never", "without", "nor ")


def _semantic_negation(claim: str, ev: str) -> Finding | None:
    cl, el = (claim or "").lower(), (ev or "").lower()
    claim_neg = any(n in cl for n in _NEG)
    ev_neg = any(n in el for n in _NEG)
    if not claim_neg or ev_neg:
        return None
    shared = set(tokens(claim)) & set(tokens(ev))
    if len(shared) >= 3 and similarity(claim, ev) >= 0.3:
        return Finding(
            rel="contradicts", hard=True, mechanism="semantic-negation",
            explanation="The pleading denies what the contemporaneous record affirms.",
        )
    return None


def surface(claim_text: str, evidence_text: str) -> Finding | None:
    """Run every deterministic surfacer; return the first (strongest) hit."""
    for fn in (_numeric_disjoint, _supersession, _contractual, _semantic_negation):
        f = fn(claim_text, evidence_text)
        if f is not None:
            f.deterministic = True          # a precise surfacer fired — trustworthy
            return f
    return None


# --------------------------------------------------------------- LLM classifier
_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "rel": {"type": "string",
                "enum": ["contradicts", "supersedes", "supports", "caps",
                         "qualifies", "attacks", "legal_bar", "none"]},
        "hard": {"type": "boolean"},
        "mechanism": {"type": "string"},
        "explanation": {"type": "string"},
        "own_goal": {"type": "boolean"},
    },
    "required": ["rel", "hard", "mechanism", "explanation", "own_goal"],
}


def classify(claim_text: str, evidence_text: str, *, evidence_party: str = "neutral",
             llm: LLM | None = None) -> Finding:
    """Name the mechanism and emit the coherence relation (bundle → pleading).

    Tries the deterministic surfacers first (they are exact and offline). If none
    fire and an LLM is available, asks it for a strict-tool-use classification;
    otherwise returns ``none``.
    """
    det = surface(claim_text, evidence_text)
    if det is not None:
        det.own_goal = det.is_contradiction and evidence_party == "claimant"
        return det
    if llm is not None and llm.available():
        out = llm.structured(
            instruction=(
                "Classify the relation of the EVIDENCE to the PLEADED claim. "
                "Name the mechanism. rel in [contradicts, supersedes, supports, "
                "caps, qualifies, attacks, legal_bar, none].\n\n"
                f"PLEADED: {claim_text}\nEVIDENCE: {evidence_text}"
            ),
            schema=_SCHEMA, model=MODEL_EXTRACT, max_tokens=400,
        )
        if out and out.get("rel"):
            f = Finding(
                rel=str(out["rel"]), hard=bool(out.get("hard", out["rel"] in _HARD)),
                mechanism=str(out.get("mechanism", "")),
                explanation=str(out.get("explanation", "")),
                own_goal=bool(out.get("own_goal", False)),
            )
            if f.is_contradiction and evidence_party == "claimant":
                f.own_goal = True
            return f
    return Finding(rel=REL_NONE)
