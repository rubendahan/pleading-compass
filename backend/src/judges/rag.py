"""Judge B — lexical RAG: retrieve the top-k most similar paragraphs, then judge ONLY those.

A classic retrieval-augmented pipeline: score every paragraph in the bundle by
lexical token-overlap with the proposition, keep the top-k, and show the model
ONLY that window. Cheap, scalable, and the obvious first thing to reach for.

THE POINT (why this judge is in the bake-off): lexical retrieval is blind to
meaning. The decisive paragraph is frequently NOT lexically similar to the
proposition. The Fujitsu engineer establishes remote access with the words
"balancing transactions inserted ... without notifying the subpostmaster",
while the proposition pleads "alter branch transaction data remotely" — almost
no shared tokens. When the deciding paragraph falls outside the retrieved
window, this judge MISSES the contradiction, or worse, hallucinates SUPPORT for
a pleaded gap because the only paragraphs it retrieved are merely topically
adjacent. High recall on the easy propositions, silent misses on the hard ones:
that is exactly the failure mode the long-context judge is meant to beat, and
exactly what the bake-off exists to expose.
"""
from __future__ import annotations

import re
from typing import Optional

from . import base, stub
from .. import llm
from ..models import Bundle, Judgement, Proposition

# Stopword-light list: drop the connective tissue so overlap reflects content.
_STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "to", "in", "on", "at", "by", "for",
    "with", "as", "that", "this", "it", "its", "is", "are", "was", "were", "be",
    "been", "being", "did", "do", "does", "not", "no", "any", "but", "if",
    "from", "into", "than", "then", "so", "such", "which", "who", "whom",
    "there", "here", "their", "they", "them", "had", "has", "have", "will",
    "would", "could", "may", "might", "shall", "should", "can", "all", "each",
}
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall((text or "").lower())
            if len(t) > 1 and t not in _STOPWORDS}


def retrieve(proposition: Proposition, bundle: Bundle, k: int = 4) -> list[tuple[str, int, float]]:
    """Lexical token-overlap retrieval.

    Score each paragraph by ``|overlap| / |proposition tokens|`` (lowercased,
    stopword-light, set intersection). Return the top-*k* as
    ``(doc_id, para, score)`` sorted by score descending.
    """
    prop = _tokens(proposition.text)
    scored: list[tuple[str, int, float]] = []
    for doc_id, para, text in bundle.iter_paras():
        score = (len(prop & _tokens(text)) / len(prop)) if prop else 0.0
        scored.append((doc_id, para, score))
    scored.sort(key=lambda row: row[2], reverse=True)
    return scored[:k]


_SYSTEM = (
    "You are a litigation analyst. Decide whether a pleaded PROPOSITION is "
    "SUPPORTED, CONTRADICTED, NOT_ADDRESSED, or UNVERIFIED by the supplied "
    "CONTEXT. The CONTEXT is a RETRIEVED SUBSET of a litigation bundle and may "
    "be incomplete. Reason ONLY from the CONTEXT. Quote VERBATIM — copy each "
    "quote word-for-word from the paragraph at its doc/para anchor; never invent "
    "or paraphrase. If the retrieved CONTEXT does not address the proposition, "
    "return NOT_ADDRESSED with empty evidence rather than guessing.\n"
    "Return ONLY this JSON object, nothing else:\n"
    '{"verdict":"SUPPORTED|CONTRADICTED|NOT_ADDRESSED|UNVERIFIED",'
    '"confidence":0.0,'
    '"evidence":[{"doc_id":"04","para":2,"quote":"<verbatim>","polarity":"support|contradict"}],'
    '"contradictions":[{"ref_a":"04¶2","ref_b":"02¶3","note":"..."}]}'
)


def _context(rows: list[tuple[str, int, float]], bundle: Bundle) -> str:
    """Render the retrieved paragraphs as ``doc¶n: text`` anchors — and only those."""
    lines: list[str] = []
    for doc_id, para, _score in rows:
        doc = bundle.get(doc_id)
        p = doc.para(para) if doc else None
        if p:
            lines.append(f"{doc_id}¶{para}: {p.text}")
    return "\n".join(lines)


def judge(proposition: Proposition, bundle: Bundle, *,
          force_stub: bool = False, model: Optional[str] = None, fallback=None) -> Judgement:
    """Retrieve the top-4 paragraphs, then judge the proposition on those alone."""
    fb = fallback or stub.judge
    if force_stub or llm.active_backend() == "offline stub":
        return fb(proposition, bundle)
    try:
        rows = retrieve(proposition, bundle, k=4)
        user = (
            f"PROPOSITION ({proposition.id}; burden on {proposition.burden}):\n"
            f"{proposition.text}\n\n"
            f"CONTEXT (top-{len(rows)} retrieved paragraphs, anchored doc¶n):\n"
            f"{_context(rows, bundle)}"
        )
        text, backend = llm.chat(_SYSTEM, user, model=model)
        data = llm.parse_json(text)
        return base.build_judgement(proposition, bundle, data, backend=backend)
    except Exception:
        return fb(proposition, bundle)


def make_judge(*, force_stub: bool = False, model: Optional[str] = None,
               key=None) -> base.JudgeFn:
    """Offline / on error defers to the stub bound to the same answer *key*."""
    fallback = stub.make_judge(key=key)

    def _judge(proposition: Proposition, bundle: Bundle) -> Judgement:
        return judge(proposition, bundle, force_stub=force_stub, model=model, fallback=fallback)
    return _judge
