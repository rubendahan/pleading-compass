"""Phase 0a — extract atomic claims from the pleading, with HARD coverage.

Every paragraph of the pleading yields at least one pleading `ClaimNode` and a
resolvable proposition. A paragraph carrying a provided allegation is mapped to
that proposition; a paragraph with no allegation still emits an explicit
synthesized proposition (default verdict NOT_ADDRESSED) — it is NEVER skipped.
This is what makes the "02¶6 has no status" bug unreachable.
"""
from __future__ import annotations

import re

from .embed import Embedder
from .lexical import best_quote
from .models import Bundle, ClaimNode

# Coarse issue buckets — a deterministic keyword classifier. The token is shared
# verbatim by a claim and its cluster (the spec's issue join key).
_ISSUE_RULES = [
    ("DELAY/SCOPE", ("late", "go-live", "go live", "delay", "deadline", "scope",
                     "change", "schedule", "deliver")),
    ("ACCEPTANCE", ("accept", "sign-off", "sign off", "uat", "certificate")),
    ("DEFECTS", ("defect", "severity", "fault", "fit for purpose", "satisfactory",
                 "unavailab", "outage")),
    ("REPRESENTATION", ("represent", "concurrent", "warrant", "misrepresent")),
    ("TRAINING", ("train", "training")),
    ("QUANTUM/CAP", ("loss", "profit", "expenditure", "damages", "£", "gbp",
                     "cap", "liability", "interest")),
]


def issue_for(text: str) -> str:
    t = (text or "").lower()
    for issue, kws in _ISSUE_RULES:
        if any(k in t for k in kws):
            return issue
    return "PLEADINGS"


def _pleading_tab(bundle: Bundle, propositions: list[dict]) -> str:
    counts: dict[str, int] = {}
    for p in propositions:
        tab = p.get("pleaded_at", (None, None))[0]
        if tab:
            counts[tab] = counts.get(tab, 0) + 1
    if counts:
        return max(counts, key=lambda t: (counts[t], t == "02", t))
    for d in bundle.docs:
        if d.doc_type == "pleading" and d.party == "claimant":
            return d.id
    return bundle.docs[0].id if bundle.docs else "02"


def extract_claims(bundle: Bundle, propositions: list[dict], *,
                   embedder: Embedder) -> tuple[list[ClaimNode], list[dict]]:
    """Return ``(claims, propositions)`` covering EVERY pleading paragraph.

    ``propositions`` is the input list augmented with synthesized entries for any
    pleading paragraph that no provided proposition was pleaded at.
    """
    tab = _pleading_tab(bundle, propositions)
    pleading = bundle.get(tab)

    # Group provided propositions by the paragraph they are pleaded at.
    by_para: dict[int, list[dict]] = {}
    for p in propositions:
        at = p.get("pleaded_at") or (tab, 0)
        if str(at[0]) == tab:
            by_para.setdefault(int(at[1]), []).append(p)

    claims: list[ClaimNode] = []
    out_props: list[dict] = list(propositions)
    seen_props = {p["id"] for p in propositions}

    paras = pleading.paras if pleading else []
    for para in paras:
        mapped = by_para.get(para.n, [])
        if mapped:
            for prop in mapped:
                claims.append(_make_claim(prop["id"], prop.get("text") or para.text,
                                          tab, para.n, para.text, embedder))
        else:
            # No allegation here — still emit an explicit proposition + claim so
            # the paragraph is never left without a verdict.
            pid = f"U{tab}_{para.n}"
            if pid not in seen_props:
                out_props.append({
                    "id": pid, "text": para.text, "pleaded_at": (tab, para.n),
                    "synthesized": True,
                })
                seen_props.add(pid)
            claims.append(_make_claim(pid, para.text, tab, para.n, para.text, embedder))

    return claims, out_props


def _make_claim(prop_id: str, prop_text: str, tab: str, n: int, para_text: str,
                embedder: Embedder) -> ClaimNode:
    quote = best_quote(prop_text, para_text)
    cid = f"p_{tab}_{n}_{re.sub(r'[^A-Za-z0-9]', '', prop_id)}"
    return ClaimNode(
        id=cid, prop_id=prop_id, text=prop_text, quote=quote, tab=tab, para=n,
        embedding=embedder.embed(prop_text), issue=issue_for(prop_text),
    )
