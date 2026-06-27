"""Pleaded propositions: the units we stress-test against the bundle.

`seed_propositions()` returns the labelled self-test set. `extract_propositions`
uses the LLM to pull atomic pleaded propositions from the `pleading` documents
in a real bundle, and falls back to the seeds offline / on error.
"""
from __future__ import annotations

from typing import Optional

from .models import Bundle, Proposition


def seed_propositions() -> list[Proposition]:
    from data.selftest.propositions import PROPOSITIONS
    return list(PROPOSITIONS)


_SYSTEM = (
    "You extract atomic pleaded propositions from litigation pleadings. "
    "Return ONLY a JSON array; each item: "
    '{"id","text","party":"claimant|defendant","kind":"allegation|defence",'
    '"burden":"claimant|defendant"}. One self-contained proposition each.'
)


def extract_propositions(bundle: Bundle, *, force_stub: bool = False,
                         model: Optional[str] = None) -> list[Proposition]:
    from . import llm
    if force_stub or llm.active_backend() == "offline stub":
        return seed_propositions()
    pleadings = [d for d in bundle.docs if d.doc_type == "pleading"]
    if not pleadings:
        return seed_propositions()
    text = "\n\n".join(
        f"### {d.id} {d.title} ({d.party})\n" + "\n".join(f"¶{p.n} {p.text}" for p in d.paras)
        for d in pleadings
    )
    try:
        out, _ = llm.chat(_SYSTEM, text, model=model)
        data = llm.parse_json(out)
        props = [
            Proposition(
                id=str(it["id"]), text=str(it["text"]),
                party=str(it.get("party", "claimant")), kind=str(it.get("kind", "allegation")),
                burden=str(it.get("burden", it.get("party", "claimant"))),
            )
            for it in data
        ]
        return props or seed_propositions()
    except Exception:
        return seed_propositions()
