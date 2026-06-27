"""Judge registry. Each module exposes ``make_judge(*, force_stub, model) -> JudgeFn``.

LLM judges (Phase 2) import lazily so the skeleton runs before they exist:
``available()`` lists only the judges whose module imports cleanly.
"""
from __future__ import annotations

import importlib
from typing import Optional

from .base import JudgeFn

_REGISTRY = {
    "stub": "src.judges.stub",
    "longcontext": "src.judges.longcontext",
    "rag": "src.judges.rag",
    "argument": "src.judges.argument",
    "numeric": "src.judges.numeric",
    "panel": "src.judges.panel",
    "logit": "src.judges.logit",
}


def get_judge(name: str, *, force_stub: bool = False, model: Optional[str] = None,
              key=None) -> JudgeFn:
    if name not in _REGISTRY:
        raise KeyError(f"unknown judge '{name}' (have: {', '.join(_REGISTRY)})")
    mod = importlib.import_module(_REGISTRY[name])
    # The stub IS the answer key; the LLM judges use it as their offline fallback.
    return mod.make_judge(force_stub=force_stub, model=model, key=key)


def available() -> list[str]:
    out = []
    for name, modpath in _REGISTRY.items():
        try:
            importlib.import_module(modpath)
            out.append(name)
        except Exception:
            pass
    return out
