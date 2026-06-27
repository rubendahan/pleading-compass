"""Deterministic source-grounding helpers used by the mapper.

The pipeline's findings are LLM-derived. Before the front end renders any
verdict we re-anchor it to a *verbatim* paragraph quote, so every claim shown to
a user can be checked against the literal text of the source document. These
helpers do that re-grounding with a pure-Python, offline, fully reproducible
method (no embeddings, no network): a cosine over content-token term-frequency
vectors to find the most on-point paragraph and sentence, and a hard substring
check to guarantee the quote is literally present in the source.

Two jobs:
  * paragraph splitting: turn a raw document into numbered paragraphs, so a
    quote can be anchored to "<tab>paragraph<n>".
  * verbatim quoting: pick the most relevant sentence of a paragraph and prove
    it is an exact substring of that paragraph.
"""
from __future__ import annotations

import math
import re
from collections import Counter

# Common words carry little signal; dropping them sharpens the lexical match.
_STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "to", "in", "on", "at", "by", "for",
    "with", "as", "that", "this", "it", "its", "is", "are", "was", "were", "be",
    "been", "being", "did", "do", "does", "not", "no", "any", "but", "if",
    "from", "into", "than", "then", "so", "such", "which", "who", "whom",
    "there", "here", "their", "they", "them", "had", "has", "have", "will",
    "would", "could", "may", "might", "shall", "should", "can", "all", "each",
}
_TOKEN = re.compile(r"[a-z0-9]+")
_SENT = re.compile(r"[^.!?]*[.!?]")


def tokens(text: str) -> list[str]:
    """Content tokens of *text*: lowercased alphanumerics, stopwords removed."""
    return [t for t in _TOKEN.findall((text or "").lower())
            if len(t) > 1 and t not in _STOPWORDS]


def similarity(query: str, text: str) -> float:
    """Cosine over content-token term-frequency vectors, in [0, 1].

    Explainable to a court: shared content words, frequency-weighted, normalised
    for length. Used to pick the paragraph/sentence most on-point to a finding.
    """
    q, p = Counter(tokens(query)), Counter(tokens(text))
    if not q or not p:
        return 0.0
    dot = sum(q[t] * p[t] for t in q.keys() & p.keys())
    norm = math.sqrt(sum(v * v for v in q.values())) * math.sqrt(sum(v * v for v in p.values()))
    return dot / norm if norm else 0.0


def best_quote(prop_text: str, para_text: str) -> str:
    """Pick the sentence of *para_text* most on-point to *prop_text*.

    The returned value is always an exact substring of *para_text* (we slice the
    original sentences, never re-join), so it satisfies the verbatim invariant.
    Falls back to the whole paragraph when no sentence stands out.
    """
    para_text = para_text or ""
    spans = [m.group(0).strip() for m in _SENT.finditer(para_text)]
    spans = [s for s in spans if s and s in para_text]
    if not spans:
        return para_text.strip()
    best, best_score = para_text.strip(), -1.0
    for s in spans:
        score = similarity(prop_text, s)
        if score > best_score:
            best, best_score = s, score
    # Only prefer a sentence if it actually overlaps; else keep whole paragraph.
    return best if best_score > 0 else para_text.strip()


def verbatim_ok(quote: str, para_text: str) -> bool:
    """Hard invariant: the quote must be a literal substring of the paragraph."""
    return bool(quote) and quote in (para_text or "")


def paragraphs(body: str) -> list[tuple[int, str]]:
    """Split a document body into numbered paragraphs ``[(n, text), ...]``.

    Paragraphs are blank-line separated; each is whitespace-reflowed to a single
    line and numbered sequentially from 1. This numbering is what an anchor of
    the form "<tab>paragraph<n>" points at.
    """
    chunks = re.split(r"\n\s*\n", (body or "").strip())
    out: list[tuple[int, str]] = []
    n = 0
    for ch in chunks:
        text = re.sub(r"\s+", " ", ch.strip())
        if not text:
            continue
        n += 1
        out.append((n, text))
    return out
