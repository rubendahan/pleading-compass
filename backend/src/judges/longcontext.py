"""Long-context judge — feeds the WHOLE bundle to the model, no retrieval.

Judge "A" of the bake-off: one prompt per proposition containing every
document (numbered paragraphs) via ``Bundle.full_text()``. Relies on the model
to read the whole bundle and reason globally — cross-document contradictions,
silence, single-source risk — rather than chunk-and-retrieve. The shared
``base.build_judgement`` maps the JSON contract identically for every LLM judge
and drops any non-verbatim (hallucinated) quote. No key / any error -> the
deterministic offline stub.
"""
from __future__ import annotations

from typing import Optional

from . import base, stub
from .. import llm
from ..models import Bundle, Judgement, Proposition

_SYSTEM = (
    "You are a meticulous litigation analyst. Read the WHOLE bundle of documents "
    "below (each shown as '### <doc_id> <title>' followed by numbered paragraphs "
    "'¶n'). Classify the single pleaded proposition as SUPPORTED, "
    "CONTRADICTED, NOT_ADDRESSED, or UNVERIFIED on the evidence in the bundle.\n"
    "Return ONLY JSON of this exact shape:\n"
    '{"verdict":"...","confidence":0.0,'
    '"evidence":[{"doc_id":"04","para":2,'
    '"quote":"<verbatim sentence copied from that doc>","polarity":"support|contradict"}],'
    '"contradictions":[{"ref_a":"04¶2","ref_b":"02¶3","note":"..."}]}\n'
    "Rules: every quote MUST be copied verbatim from the cited document — NEVER "
    "invent or paraphrase a quote. Use verdict NOT_ADDRESSED with empty evidence "
    "when the bundle is silent on the proposition. Flag cross-document "
    "contradictions (e.g. a witness statement contradicting a pleaded denial) in "
    "the 'contradictions' array using '<doc_id>¶<para>' anchors."
)


def _user_prompt(proposition: Proposition, bundle: Bundle) -> str:
    return (
        f"PLEADED PROPOSITION\n"
        f"id: {proposition.id}\n"
        f"party: {proposition.party}\n"
        f"kind: {proposition.kind}\n"
        f"text: {proposition.text}\n\n"
        f"BUNDLE\n{bundle.full_text()}"
    )


def make_judge(*, force_stub: bool = False, model: Optional[str] = None,
               key=None) -> base.JudgeFn:
    """Return a ``judge(proposition, bundle)`` closure binding *model*/*force_stub*.
    Offline / on error it defers to the stub bound to the same answer *key*."""
    fallback = stub.make_judge(key=key)

    def _judge(proposition: Proposition, bundle: Bundle) -> Judgement:
        if force_stub or llm.active_backend() == "offline stub":
            return fallback(proposition, bundle)
        try:
            text, label = llm.chat(_SYSTEM, _user_prompt(proposition, bundle), model=model)
            data = llm.parse_json(text)
            return base.build_judgement(proposition, bundle, data, backend=label)
        except Exception:
            return fallback(proposition, bundle)

    return _judge


def judge(proposition: Proposition, bundle: Bundle) -> Judgement:
    """Module-level convenience judge with default binding."""
    return make_judge()(proposition, bundle)
