"""Data model for engine_v2 — the claim+evidence graph and its outputs.

A `Bundle` is a litigation bundle (pleadings + evidence). The engine extracts a
`ClaimNode` from every pleaded paragraph, builds an `EvidenceNode` for every
bundle paragraph (embedding + NL description), links claim↔evidence by cosine,
and emits one `Assessment` per pleaded proposition: a verdict
(SUPPORTED / CONTRADICTED / NOT_ADDRESSED / UNVERIFIED) with a verbatim
source-anchored quote, a calibrated confidence and a VERIFY flag.

These shapes are the shared contract every engine_v2 module depends on. They are
re-implemented here (not imported from ``src``) so this package stands alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

VERDICTS = ("SUPPORTED", "CONTRADICTED", "NOT_ADDRESSED", "UNVERIFIED")

# Legal-risk overlays, independent of the factual verdict (per BACKEND-OUTPUT-SPEC).
OVERLAYS = (
    "NONE", "CONTRACTUALLY_BARRED", "SUPERSEDED", "CAPPED",
    "CAUSATION_PROBLEM", "BURDEN_PROBLEM",
)

# Coherence edge relations (bundle claim → pleading claim).
RELATIONS = (
    "asserts", "contradicts", "supersedes", "supports", "caps",
    "qualifies", "attacks", "legal_bar", "belongs_to",
)


# --------------------------------------------------------------------------- bundle
@dataclass
class Para:
    n: int
    text: str


@dataclass
class Document:
    id: str                         # short stable tab id, e.g. "02"
    title: str
    doc_type: str                   # pleading | witness | expert | contract | record | correspondence
    party: str                      # claimant | defendant | neutral
    date: Optional[str] = None
    paras: list[Para] = field(default_factory=list)
    category: Optional[str] = None
    modality: str = "document"
    mime: str = "text/plain"
    file_url: Optional[str] = None
    description: Optional[str] = None

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

    def para_text(self, doc_id: str, n: int) -> str:
        d = self.get(doc_id)
        if not d:
            return ""
        p = d.para(n)
        return p.text if p else ""


# --------------------------------------------------------------------------- graph
@dataclass
class ClaimNode:
    """An atomic pleaded allegation extracted from the pleading."""
    id: str                         # stable id, e.g. "p_02_8"
    prop_id: str                    # proposition label, e.g. "P2" / "U02_6"
    text: str                       # the allegation, plain prose
    quote: str                      # verbatim substring of the pleaded paragraph
    tab: str                        # pleading tab id (usually "02")
    para: int                       # paragraph number it is pleaded at
    embedding: list[float] = field(default_factory=list)
    issue: str = "GENERAL"
    party: str = "claimant"

    @property
    def anchor(self) -> str:
        return f"{self.tab}¶{self.para}"


@dataclass
class EvidenceNode:
    """A quote-grounded fact from the bundle (one per bundle paragraph)."""
    doc_id: str
    para: int
    text: str
    time: Optional[str] = None      # parsed ISO-ish date, if any
    ev_type: str = "record"         # source_type vocabulary (signed_contract, expert_report, ...)
    nl_description: str = ""         # normalised text / multimodal description
    embedding: list[float] = field(default_factory=list)
    source_strength: float = 3.0    # weight convention: docs ~5, experts ~4, witnesses ~2

    @property
    def id(self) -> str:
        return f"e_{self.doc_id}_{self.para}"

    @property
    def anchor(self) -> str:
        return f"{self.doc_id}¶{self.para}"


@dataclass
class Edge:
    source: str                     # node id
    target: str                     # node id
    rel: str                        # one of RELATIONS
    kind: str                       # provenance | coherence | impact
    hard: bool = False
    explanation: str = ""
    mechanism: str = ""             # named mechanism (numeric / date / supersession / ...)
    own_goal: bool = False
    verdict: Optional[str] = None   # carried on belongs_to edges
    load_bearing: bool = False
    blocking: bool = False


@dataclass
class Graph:
    claims: list[ClaimNode] = field(default_factory=list)
    evidence: list[EvidenceNode] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    # claim id -> [(EvidenceNode, cosine), ...] descending
    links: dict[str, list[tuple[EvidenceNode, float]]] = field(default_factory=dict)


@dataclass
class Assessment:
    prop_id: str
    verdict: str                    # one of VERDICTS
    legal_risk: str                 # one of OVERLAYS
    quote: str                      # verbatim controlling-evidence quote ("" if none)
    anchor: str                     # "<tab>¶<para>" of the controlling evidence ("" if none)
    confidence: float               # calibrated, [0, 1]
    verify: bool                    # raise the human-verify flag
    reasons: list[str] = field(default_factory=list)
    evidence: list[tuple[str, int]] = field(default_factory=list)  # (tab, para) anchors
    single_source: bool = False
    coverage: Optional[dict] = None  # search-proof for NOT_ADDRESSED


def make_anchor(doc_id: str, para: int) -> str:
    """Anchor in the canonical ``<tab>¶<para>`` form (pilcrow U+00B6)."""
    return f"{doc_id}¶{para}"
