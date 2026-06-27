"""Logit-confidence judge — NVIDIA Nemotron, used through its internals.

Most judges sample/argmax a verdict token and throw the distribution away. This judge
keeps it: it constrains the model to answer with a single letter (A/B/C/D mapped to the
four verdicts), reads the **logits over exactly those four label tokens**, and softmaxes
them into a calibrated distribution. The top probability is the confidence, the margin and
normalised entropy are the uncertainty — a far better signal than asking a model to score
its own confidence in prose.

Why this is the Nemotron / GPU angle: logit access needs the model's internals, so it runs
the open Nemotron weights **locally on the GPU** (HF transformers) and reads
``model(...).logits[0, -1]`` over the label token ids. It composes with ``confidence.py``:
the panel can blend this *intra-model* uncertainty with *inter-judge* disagreement.

Degrades safely: no ``logits_fn``, no torch/transformers, no model -> the deterministic
offline stub. Evidence anchoring is borrowed from the stub (logits give a verdict and a
confidence, not quotes); the verbatim anchors stay deterministic.
"""
from __future__ import annotations

import math
import os
from typing import Callable, Optional

from . import base, stub
from ..models import Bundle, Judgement, Proposition, VERDICTS

# Single-token labels, aligned to VERDICTS order (SUPPORTED, CONTRADICTED, NOT_ADDRESSED, UNVERIFIED).
LABELS = ["A", "B", "C", "D"]

LogitsFn = Callable[[str], list]


def _softmax(xs: list[float]) -> list[float]:
    m = max(xs)
    es = [math.exp(x - m) for x in xs]
    s = sum(es) or 1.0
    return [e / s for e in es]


def logit_confidence(logits: list[float]) -> dict:
    """Turn four verdict logits into a calibrated distribution + confidence.

    Returns ``{verdict, confidence, margin, entropy, dist}`` where ``verdict`` is the
    argmax, ``confidence`` the top probability, ``margin`` top minus runner-up, and
    ``entropy`` the normalised Shannon entropy in ``[0, 1]`` (0 = certain, 1 = uniform)."""
    probs = _softmax(list(logits)[:len(VERDICTS)])
    order = sorted(range(len(probs)), key=lambda i: -probs[i])
    top = order[0]
    second = probs[order[1]] if len(order) > 1 else 0.0
    n = len(probs)
    h = (-sum(p * math.log(p) for p in probs if p > 0) / math.log(n)) if n > 1 else 0.0
    return {
        "verdict": VERDICTS[top],
        "confidence": probs[top],
        "margin": probs[top] - second,
        "entropy": min(1.0, max(0.0, h)),
        "dist": {VERDICTS[i]: probs[i] for i in range(len(probs))},
    }


_SYSTEM = (
    "You are a litigation analyst. Decide whether the pleaded PROPOSITION is, on the "
    "BUNDLE: A) SUPPORTED, B) CONTRADICTED, C) NOT_ADDRESSED, D) UNVERIFIED. "
    "Answer with the single letter only."
)


def _prompt(proposition: Proposition, bundle: Bundle) -> str:
    return (f"{_SYSTEM}\n\nPROPOSITION ({proposition.id}; burden on {proposition.burden}):\n"
            f"{proposition.text}\n\nBUNDLE\n{bundle.full_text()}\n\nAnswer (A/B/C/D):")


def make_judge(*, force_stub: bool = False, model: Optional[str] = None, key=None,
               logits_fn: Optional[LogitsFn] = None) -> base.JudgeFn:
    """Return a judge that reads a four-way verdict distribution from model logits.

    ``logits_fn(prompt) -> [4 logits]`` is the injectable seam (mocked in tests). With no
    seam and no local model it defers to the deterministic stub bound to *key*."""
    fallback = stub.make_judge(key=key)

    def _judge(proposition: Proposition, bundle: Bundle) -> Judgement:
        fn = logits_fn or _local_logits_fn(model)
        if force_stub or fn is None:
            return fallback(proposition, bundle)
        try:
            r = logit_confidence(fn(_prompt(proposition, bundle)))
            anchored = fallback(proposition, bundle)        # borrow deterministic evidence
            return Judgement(
                proposition.id, r["verdict"], r["confidence"],
                anchored.evidence, anchored.contradictions,
                single_source=anchored.single_source, burden=proposition.burden,
                backend=f"logit:{model or 'nemotron-local'}",
                extra={"dist": r["dist"], "entropy": r["entropy"], "margin": r["margin"]},
            )
        except Exception:
            return fallback(proposition, bundle)

    return _judge


def _local_logits_fn(model: Optional[str]) -> Optional[LogitsFn]:
    """A logits function backed by a LOCAL Nemotron (HF transformers) on the GPU, or None.

    Reads next-token logits over the A/B/C/D label tokens. Guarded so the module imports
    and the bake-off runs with neither torch nor a model present (then judges defer to the
    stub). Set ``NEMOTRON_LOCAL_MODEL`` (or pass ``model=``) to enable on a GPU box."""
    name = model or os.getenv("NEMOTRON_LOCAL_MODEL")
    if not name:
        return None
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception:
        return None

    tokenizer = AutoTokenizer.from_pretrained(name)
    lm = AutoModelForCausalLM.from_pretrained(name, torch_dtype="auto", device_map="auto")
    label_ids = [tokenizer.encode(lbl, add_special_tokens=False)[0] for lbl in LABELS]

    def _fn(prompt: str) -> list:
        inputs = tokenizer(prompt, return_tensors="pt").to(lm.device)
        with torch.no_grad():
            logits = lm(**inputs).logits[0, -1]
        return [float(logits[i]) for i in label_ids]

    return _fn


def judge(proposition: Proposition, bundle: Bundle) -> Judgement:
    """Module-level convenience judge (defers to the self-test stub offline)."""
    return make_judge()(proposition, bundle)
