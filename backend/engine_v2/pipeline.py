"""Orchestration: ingest → claims → evidence → graph → contradiction → assess →
safety → adapter. ``assert_coverage`` runs at the very end (fail loud)."""
from __future__ import annotations

from dataclasses import dataclass

from . import adapter, claims as claims_mod, safety
from .assess import assess
from .embed import get_embedder
from .evidence import build_evidence
from .graph import build_graph
from .ingest import coerce_bundle, coerce_propositions
from .llm import LLM
from .models import Assessment, Bundle, ClaimNode, Graph


@dataclass
class Analysis:
    bundle: Bundle
    graph: Graph
    claims: list[ClaimNode]
    propositions: list[dict]
    assessments: dict[str, Assessment]
    pleading_tab: str
    backend: str


def _bundle_prefix(bundle: Bundle, *, limit: int = 60000) -> str:
    out: list[str] = []
    for d in bundle.docs:
        out.append(f"### {d.id} {d.title} ({d.doc_type}, {d.party})")
        for p in d.paras:
            out.append(f"¶{p.n} {p.text}")
        out.append("")
    text = "\n".join(out)
    return text[:limit]


def analyze(propositions, bundle, *, offline: bool = True) -> Analysis:
    bundle_obj = coerce_bundle(bundle)
    props = coerce_propositions(propositions, bundle_obj)
    pleading_tab = claims_mod._pleading_tab(bundle_obj, props)

    embedder = get_embedder(offline=offline)
    llm = LLM(offline=offline, bundle_prefix=_bundle_prefix(bundle_obj))

    claim_nodes, props_full = claims_mod.extract_claims(bundle_obj, props, embedder=embedder)
    evidence = build_evidence(bundle_obj, embedder=embedder, exclude_tab=pleading_tab)
    graph = build_graph(claim_nodes, evidence)
    assessments = assess(graph, claim_nodes, bundle_obj, props_full,
                         llm=llm, offline=offline, pleading_tab=pleading_tab)

    return Analysis(bundle_obj, graph, claim_nodes, props_full, assessments,
                    pleading_tab, llm.backend)


def to_appdata(propositions, bundle, *, offline: bool = True,
               meta: dict | None = None, chronology: list | None = None) -> dict:
    an = analyze(propositions, bundle, offline=offline)
    appdata = adapter.to_appdata(
        an.bundle, an.graph, an.claims, an.propositions, an.assessments,
        pleading_tab=an.pleading_tab, meta=meta, chronology=chronology,
    )
    safety.assert_coverage(appdata)   # hard invariant — every pleading ¶ has a status
    return appdata
