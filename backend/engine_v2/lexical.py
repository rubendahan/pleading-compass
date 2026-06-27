"""Deterministic lexical scoring + the NOT_ADDRESSED search-proof.

Ported from ``src/coverage.py``. A pure-Python, offline cosine over content-token
term-frequency vectors — fully reproducible and explainable to a court ("shared
content words, frequency-weighted, normalised for length"). Used by the offline
assessor (support score) and the safety net (coverage proof behind an absence).
"""
from __future__ import annotations

import math
import re
from collections import Counter

DEFAULT_THRESHOLD = 0.55

_STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "to", "in", "on", "at", "by", "for",
    "with", "as", "that", "this", "it", "its", "is", "are", "was", "were", "be",
    "been", "being", "did", "do", "does", "not", "no", "any", "but", "if",
    "from", "into", "than", "then", "so", "such", "which", "who", "whom",
    "there", "here", "their", "they", "them", "had", "has", "have", "will",
    "would", "could", "may", "might", "shall", "should", "can", "all", "each",
}
_TOKEN = re.compile(r"[a-z0-9]+")
_CLAUSE = re.compile(r"[,;:.()—]|\band\b|\bor\b|\bbut\b|\bwithout\b|\bthat\b|\bwhich\b")


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall((text or "").lower())
            if len(t) > 1 and t not in _STOPWORDS]


def similarity(query: str, text: str) -> float:
    """Cosine over content-token term-frequency vectors, in [0, 1]."""
    q, p = Counter(tokens(query)), Counter(tokens(text))
    if not q or not p:
        return 0.0
    dot = sum(q[t] * p[t] for t in q.keys() & p.keys())
    norm = math.sqrt(sum(v * v for v in q.values())) * math.sqrt(sum(v * v for v in p.values()))
    return dot / norm if norm else 0.0


def query_variants(text: str) -> list[str]:
    """Expand a proposition into several deterministic search queries."""
    text = (text or "").strip()
    variants = [text]
    for clause in _CLAUSE.split(text):
        clause = clause.strip()
        if len(tokens(clause)) >= 2:
            variants.append(clause)
    key_terms = " ".join(tokens(text))
    if key_terms:
        variants.append(key_terms)
    seen, out = set(), []
    for q in variants:
        key = re.sub(r"\s+", " ", q.lower()).strip(" .,:;—")
        if key and key not in seen:
            seen.add(key)
            out.append(q.strip())
    return out


def coverage_search(prop_text: str, bundle, *, threshold: float = DEFAULT_THRESHOLD,
                    k: int = 5, exclude_tab: str = "") -> dict:
    """Score every bundle paragraph against every query variant — the search-proof.

    Returns a dict: ``{queries, paras_inspected, threshold, max_similarity,
    best_anchor, top_hits, crossed}``. ``crossed`` (``max>=threshold``) is the
    headline; when ``False`` for a NOT_ADDRESSED verdict, the absence is backed
    by evidence of the search itself.
    """
    queries = query_variants(prop_text)
    best_by_anchor: dict[str, float] = {}
    inspected = 0
    for doc_id, para, text in bundle.iter_paras():
        if exclude_tab and doc_id == exclude_tab:
            continue
        inspected += 1
        anchor = f"{doc_id}¶{para}"
        score = max((similarity(q, text) for q in queries), default=0.0)
        if score > best_by_anchor.get(anchor, -1.0):
            best_by_anchor[anchor] = score
    ranked = sorted(best_by_anchor.items(), key=lambda kv: (-kv[1], kv[0]))
    top_hits = [{"anchor": a, "score": round(s, 4)} for a, s in ranked[:k]]
    best_anchor, max_sim = (ranked[0][0], ranked[0][1]) if ranked else ("", 0.0)
    return {
        "queries": queries,
        "paras_inspected": inspected,
        "threshold": threshold,
        "max_similarity": round(max_sim, 4),
        "best_anchor": best_anchor,
        "top_hits": top_hits,
        "crossed": max_sim >= threshold,
    }


# ----------------------------------------------------------- verbatim quoting
_SENT = re.compile(r"[^.!?]*[.!?]")


def best_quote(prop_text: str, para_text: str) -> str:
    """Pick the sentence of *para_text* most on-point to *prop_text*.

    Returned value is always an exact substring of *para_text* (we slice the
    original, never re-join), so it satisfies the verbatim invariant. Falls back
    to the whole paragraph when no sentence stands out.
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
