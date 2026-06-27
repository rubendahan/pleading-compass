"""Phase 1 — the claim+evidence graph.

Links each pleading `ClaimNode` to its top-K `EvidenceNode`s by embedding cosine
(Benjamin's design: cosine-link claim↔evidence over the bundle), and adds
evidence↔evidence support/contradict edges among the evidence that share a claim
(co-relevant facts that corroborate or conflict with each other).
"""
from __future__ import annotations

from .contradiction import surface
from .embed import cosine
from .models import ClaimNode, Edge, EvidenceNode, Graph

_SUPPORT_SIM = 0.45


def build_graph(claims: list[ClaimNode], evidence: list[EvidenceNode], *,
                k: int = 6) -> Graph:
    g = Graph(claims=list(claims), evidence=list(evidence))
    ev_items = [(ev, ev.embedding) for ev in evidence]

    for claim in claims:
        scored = sorted(
            ((ev, cosine(claim.embedding, vec)) for ev, vec in ev_items),
            key=lambda r: (-r[1], r[0].anchor),
        )
        top = [(ev, s) for ev, s in scored[:k] if s > 0]
        g.links[claim.id] = top

        # evidence ↔ evidence edges among this claim's co-relevant facts
        chosen = [ev for ev, _ in top]
        for i in range(len(chosen)):
            for j in range(i + 1, len(chosen)):
                a, b = chosen[i], chosen[j]
                find = surface(a.text, b.text) or surface(b.text, a.text)
                if find is not None and find.is_contradiction:
                    g.edges.append(Edge(
                        source=a.id, target=b.id, rel="contradicts", kind="coherence",
                        hard=find.hard, mechanism=find.mechanism,
                        explanation=find.explanation))
                elif cosine(a.embedding, b.embedding) >= _SUPPORT_SIM:
                    g.edges.append(Edge(
                        source=a.id, target=b.id, rel="supports", kind="coherence",
                        explanation="Co-relevant facts that corroborate each other."))
    return g
