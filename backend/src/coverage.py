"""Coverage report — turn a bare NOT_ADDRESSED into a quantified search proof.

A judge that returns NOT_ADDRESSED is asserting an *absence* of evidence. A
sceptical opponent immediately asks the only question that matters: "absent, or
did you just not look hard enough?". A bare verdict cannot answer that; this
module can.

Given a proposition, ``coverage_report`` expands it into several deterministic
search queries, scores EVERY paragraph in the whole bundle against EVERY query
variant with an offline lexical similarity, and reports exactly how hard it
looked: how many query variants it ran, how many paragraphs it inspected, the
single best-matching anchor and its score, and whether that best score crossed
an acceptance threshold. The output is the defensible, quantified line a lawyer
trusts — "5 queries, 19 ¶ inspected, best lexical match 02¶2 @ 0.32 < 0.55 →
the NOT_ADDRESSED stands" — rather than an unfalsifiable "we didn't find it".

This is the grounding-confidence angle (cf. Vertex AI grounding, Luminance
confidence scoring): an absence is only credible once the search behind it is
itself verifiable. The similarity is pure-Python, deterministic and fully
offline — no LLM, no network, no surprise.

Note on what is measured: coverage is a *lexical* search proof over the whole
bundle, i.e. it answers "is this proposition topically engaged with anywhere in
the bundle?", not "is it proven?". A proposition that is pleaded or contested
(its own pleading restates it almost verbatim) will therefore score high — it
is addressed — whereas a fabricated gap that nothing in the bundle touches
stays far below threshold. That separation is the point.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .judges.base import make_anchor
from .models import Bundle, Proposition

# The acceptance threshold. Calibrated on the self-test bundle so it cleanly
# separates a proposition the bundle engages with (best lexical match well
# above) from a genuine gap that nothing in the bundle touches (well below):
# the constructed gap G1 tops out at ~0.32, the engaged propositions at ~0.69+.
DEFAULT_THRESHOLD = 0.55

# Deterministic, stopword-light tokenizer — same pattern as the lexical RAG
# judge so "what counts as a content token" is consistent across the engine.
_STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "to", "in", "on", "at", "by", "for",
    "with", "as", "that", "this", "it", "its", "is", "are", "was", "were", "be",
    "been", "being", "did", "do", "does", "not", "no", "any", "but", "if",
    "from", "into", "than", "then", "so", "such", "which", "who", "whom",
    "there", "here", "their", "they", "them", "had", "has", "have", "will",
    "would", "could", "may", "might", "shall", "should", "can", "all", "each",
}
_TOKEN = re.compile(r"[a-z0-9]+")

# Clause boundaries: punctuation and the common conjunctions/subordinators. A
# compound proposition splits into several focused sub-queries; a simple one
# does not — so "how many queries" is itself an honest signal of complexity.
_CLAUSE = re.compile(r"[,;:.()—]|\band\b|\bor\b|\bbut\b|\bwithout\b|\bthat\b|\bwhich\b")


def _tokens(text: str) -> list[str]:
    """Lowercased content tokens (stopword-light), kept as a list so term
    frequency survives for the cosine."""
    return [t for t in _TOKEN.findall((text or "").lower())
            if len(t) > 1 and t not in _STOPWORDS]


@dataclass
class CoverageReport:
    """A quantified, defensible record of how hard the bundle was searched.

    ``crossed`` is the headline: ``max_similarity >= threshold``. When it is
    ``False`` for a NOT_ADDRESSED verdict, the absence is backed by evidence of
    the search itself (``queries`` run, ``paras_inspected`` scored).
    """
    prop_id: str
    queries: list[str]
    paras_inspected: int
    threshold: float
    max_similarity: float
    best_anchor: str
    top_hits: list[tuple[str, float]]   # (anchor, score), score descending
    crossed: bool


def query_variants(proposition: Proposition) -> list[str]:
    """Deterministically expand a proposition into several search queries.

    The full pleaded text, PLUS each clause split on punctuation/conjunctions
    (so a compound allegation is probed clause-by-clause), PLUS a key-terms-only
    query of the content tokens. Near-duplicates (differing only by punctuation
    or whitespace) are collapsed, so the count reflects genuinely distinct
    probes — that is what licenses the claim "we ran N query variants".
    """
    text = proposition.text.strip()
    variants = [text]
    for clause in _CLAUSE.split(text):
        clause = clause.strip()
        if len(_tokens(clause)) >= 2:
            variants.append(clause)
    key_terms = " ".join(_tokens(text))
    if key_terms:
        variants.append(key_terms)

    seen: set[str] = set()
    out: list[str] = []
    for q in variants:
        key = re.sub(r"\s+", " ", q.lower()).strip(" .,:;—")
        if key and key not in seen:
            seen.add(key)
            out.append(q.strip())
    return out


def similarity(query: str, text: str) -> float:
    """Deterministic offline lexical similarity in [0, 1].

    Cosine over content-token term-frequency vectors. No embeddings, no model:
    fully reproducible and explainable to a court ("shared content words,
    frequency-weighted, normalised for length").
    """
    q, p = Counter(_tokens(query)), Counter(_tokens(text))
    if not q or not p:
        return 0.0
    dot = sum(q[t] * p[t] for t in q.keys() & p.keys())
    norm = math.sqrt(sum(v * v for v in q.values())) * math.sqrt(sum(v * v for v in p.values()))
    return dot / norm if norm else 0.0


def coverage_report(proposition: Proposition, bundle: Bundle, *,
                    threshold: float = DEFAULT_THRESHOLD, k: int = 5,
                    exclude_anchors: Iterable[str] = (), embedder=None) -> CoverageReport:
    """Score every paragraph in the bundle against every query variant.

    ``max_similarity`` is the best score over all (query, paragraph) pairs;
    ``best_anchor`` is where it occurred; ``paras_inspected`` is the honest
    count of paragraphs actually scored; ``top_hits`` is the top-*k*
    unique-anchor matches (descending); ``crossed`` is ``max_similarity >=
    threshold``.

    ``exclude_anchors`` drops specific anchors (e.g. the proposition's OWN
    pleading paragraph) before scoring, so a pleaded-but-unproven allegation
    cannot "cross" merely by matching its own restatement in the pleadings —
    the search then measures *independent* engagement only.

    With an ``embedder`` (e.g. ``retrieval.get_embedder()`` → Vertex embeddings),
    similarity is semantic cosine instead of lexical overlap, catching paragraphs
    that are on-point but not word-similar. Default stays lexical (offline, exact).
    """
    queries = query_variants(proposition)
    excluded = set(exclude_anchors)

    if embedder is not None:
        from .retrieval import cosine
        qvecs = [embedder.embed(q) for q in queries]
        def score_para(text: str) -> float:
            tv = embedder.embed(text)
            return max((cosine(qv, tv) for qv in qvecs), default=0.0)
    else:
        def score_para(text: str) -> float:
            return max((similarity(q, text) for q in queries), default=0.0)

    best_by_anchor: dict[str, float] = {}
    paras_inspected = 0
    for doc_id, para, text in bundle.iter_paras():
        anchor = make_anchor(doc_id, para)
        if anchor in excluded:
            continue
        paras_inspected += 1
        score = score_para(text)
        if score > best_by_anchor.get(anchor, -1.0):
            best_by_anchor[anchor] = score

    # Rank by score descending, anchor ascending for a stable deterministic order.
    ranked = sorted(best_by_anchor.items(), key=lambda kv: (-kv[1], kv[0]))
    top_hits = [(anchor, round(score, 4)) for anchor, score in ranked[:k]]
    best_anchor, max_similarity = (ranked[0][0], ranked[0][1]) if ranked else ("", 0.0)

    return CoverageReport(
        prop_id=proposition.id,
        queries=queries,
        paras_inspected=paras_inspected,
        threshold=threshold,
        max_similarity=max_similarity,
        best_anchor=best_anchor,
        top_hits=top_hits,
        crossed=max_similarity >= threshold,
    )


def render_coverage(report: CoverageReport) -> str:
    """One tight, plain-text line — the search proof a practitioner reads."""
    rel = ">=" if report.crossed else "<"
    outcome = ("topic is engaged in the bundle — verify before relying on a gap"
               if report.crossed else "absence stands")
    return (f"Coverage for [{report.prop_id}]: {len(report.queries)} queries · "
            f"{report.paras_inspected} ¶ inspected · best {report.best_anchor or '—'} @ "
            f"{report.max_similarity:.2f} {rel} {report.threshold:.2f} → {outcome}")
