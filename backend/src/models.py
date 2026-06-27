"""Core data model for the pleading-to-proof engine.

A `Bundle` is a litigation bundle (pleadings, witness statements, expert
reports, contracts, correspondence). A `Proposition` is a pleaded
allegation/defence. A judge maps a proposition to a `Judgement`:
SUPPORTED / CONTRADICTED / NOT_ADDRESSED / UNVERIFIED, with source-anchored
verbatim evidence, cross-document contradictions, and practitioner metadata
(single-source risk, burden of proof).

These shapes are the shared contract every module and every judge depends on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

VERDICTS = ("SUPPORTED", "CONTRADICTED", "NOT_ADDRESSED", "UNVERIFIED")
EVIDENCE_TYPES = (
    "contemporaneous_doc", "admission", "witness_recollection",
    "expert_opinion", "correspondence",
)


@dataclass
class Para:
    n: int
    text: str


@dataclass
class Document:
    id: str                 # short stable id, e.g. "04"
    title: str
    doc_type: str           # pleading | witness | expert | contract | correspondence
    party: str              # claimant | defendant | neutral
    date: Optional[str]
    paras: list[Para] = field(default_factory=list)

    def para(self, n: int) -> Optional[Para]:
        for p in self.paras:
            if p.n == n:
                return p
        return None


@dataclass
class Bundle:
    docs: list[Document] = field(default_factory=list)

    def get(self, doc_id: str) -> Optional[Document]:
        for d in self.docs:
            if d.id == doc_id:
                return d
        return None

    def iter_paras(self) -> Iterator[tuple[str, int, str]]:
        for d in self.docs:
            for p in d.paras:
                yield d.id, p.n, p.text

    def full_text(self) -> str:
        """All documents, numbered paragraphs — fed whole to long-context judges."""
        out: list[str] = []
        for d in self.docs:
            out.append(f"### {d.id} {d.title} ({d.doc_type}, {d.party})")
            for p in d.paras:
                out.append(f"¶{p.n} {p.text}")
            out.append("")
        return "\n".join(out)


@dataclass
class Proposition:
    id: str                 # e.g. "P1", "D2", "G1"
    text: str
    party: str              # who pleads it: claimant | defendant
    kind: str               # allegation | defence
    burden: str             # who must prove it: claimant | defendant


@dataclass
class EvidenceItem:
    doc_id: str
    para: int
    quote: str              # verbatim, copied from the source paragraph
    polarity: str           # support | contradict
    type: str               # one of EVIDENCE_TYPES
    weight: str             # high | medium | low


@dataclass
class Contradiction:
    ref_a: str              # anchor like "04¶3"
    ref_b: str              # anchor like "02¶5"
    note: str = ""


@dataclass
class Judgement:
    proposition_id: str
    verdict: str            # one of VERDICTS
    confidence: float
    evidence: list[EvidenceItem] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    single_source: bool = False
    burden: str = "claimant"
    backend: str = ""
    extra: dict = field(default_factory=dict)   # judge-specific (e.g. argument graph)
