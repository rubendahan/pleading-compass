"""Graph + Assessments → the AppData dict (BACKEND-OUTPUT-SPEC.md).

Emits the five required keys (meta/stats/nodes/edges/clusters) and the overlays
(documents/doc_index/chronology). Node id prefixes are ``prop:`` / ``claim:`` /
``doc:``; anchors are ``<tab>¶<para>`` (pilcrow). Coherence edges run BUNDLE →
PLEADING (source = bundle/legal claim, target = pleading claim). Every emitted
``quote`` is verified to be a verbatim substring of its cited paragraph
(``verbatim_ok``) — non-verbatim quotes are dropped, never invented.
"""
from __future__ import annotations

import re

from .claims import issue_for
from .contradiction import classify
from .lexical import best_quote, verbatim_ok
from .models import Assessment, Bundle, ClaimNode, Graph

_CATEGORY = {
    "pleading": "Pleading", "contract": "Contract", "expert": "Witness (expert)",
    "witness": "Witness (fact)", "correspondence": "Correspondence", "record": "Record",
}
_MONEY = re.compile(r"(?:£|gbp\s*)\s*([\d,]+(?:\.\d+)?)", re.I)


def _readiness(verdict: str, verify: bool) -> int:
    if verdict == "SUPPORTED":
        return 70 if verify else 100
    if verdict == "UNVERIFIED":
        return 40
    if verdict == "NOT_ADDRESSED":
        return 10
    return 0  # CONTRADICTED


def _fmt_money(v: float) -> str:
    if v >= 1_000_000:
        return f"£{v / 1_000_000:.1f}m"
    if v >= 1_000:
        return f"£{v / 1_000:.0f}k"
    return f"£{v:.0f}"


def _money_in(text: str) -> list[float]:
    out = []
    for m in _MONEY.finditer(text or ""):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    return out


def to_appdata(bundle: Bundle, graph: Graph, claims: list[ClaimNode],
               propositions: list[dict], assessments: dict[str, Assessment], *,
               pleading_tab: str = "02", meta: dict | None = None,
               chronology: list | None = None) -> dict:
    meta = meta or {}
    claim_by_prop: dict[str, ClaimNode] = {}
    for c in claims:
        claim_by_prop.setdefault(c.prop_id, c)
    evidence_by_anchor = {ev.anchor: ev for ev in graph.evidence}
    party = {d.id: d.party for d in bundle.docs}

    nodes: list[dict] = []
    edges: list[dict] = []
    cited_tabs: set[str] = {pleading_tab}
    issue_of_prop: dict[str, str] = {}

    # ---------------------------------------------------------- propositions
    for prop in propositions:
        pid = prop["id"]
        a = assessments.get(pid)
        verdict = a.verdict if a else "UNVERIFIED"
        overlay = a.legal_risk if a else "NONE"
        verify = a.verify if a else True
        conf = a.confidence if a else 0.0
        claim = claim_by_prop.get(pid)
        issue = claim.issue if claim else issue_for(prop.get("text", ""))
        issue_of_prop[pid] = issue
        node = {
            "id": f"prop:{pid}", "layer": "proposition", "label": pid,
            "verdict": verdict, "overlay": overlay,
            "readiness": _readiness(verdict, verify),
            "text": prop.get("text", ""),
            "confidence": conf, "verify": verify,           # forward-compat fields
        }
        if verify:
            node["source"] = "ai"                           # verify -> "AI · verify"
        nodes.append(node)

    # ---------------------------------------------------------- pleading claims
    for claim in claims:
        a = assessments.get(claim.prop_id)
        verdict = a.verdict if a else "UNVERIFIED"
        c_verdict = "accepted" if verdict == "SUPPORTED" else "rejected"
        para_text = bundle.para_text(claim.tab, claim.para)
        quote = claim.quote if verbatim_ok(claim.quote, para_text) else para_text
        nodes.append({
            "id": f"claim:{claim.id}", "layer": "claim", "label": claim.text[:42],
            "fulltext": claim.text, "issue": claim.issue, "polarity": "pleading",
            "source_type": "pleading", "weight": 1.0, "verdict": c_verdict,
            "anchor": claim.anchor, "quote": quote, "prop": claim.prop_id,
            "load_bearing": False,
            "single_source": bool(a.single_source) if a else False,
            "confidence": a.confidence if a else 0.0,
            "verify": a.verify if a else True,
        })
        # impact: pleading claim -> proposition
        edges.append({
            "source": f"claim:{claim.id}", "target": f"prop:{claim.prop_id}",
            "kind": "impact", "rel": "belongs_to", "hard": False, "verdict": c_verdict,
        })

    # ---------------------------------------------------- bundle (evidence) claims
    seen_bundle: set[str] = set()
    for prop in propositions:
        pid = prop["id"]
        a = assessments.get(pid)
        if not a or not a.anchor:
            continue
        ev = evidence_by_anchor.get(a.anchor)
        claim = claim_by_prop.get(pid)
        if ev is None or claim is None:
            continue
        cited_tabs.add(ev.doc_id)
        bid = f"claim:{ev.id}"
        # relation of this evidence to the pleading claim (deterministic in adapter)
        if a.verdict == "CONTRADICTED":
            find = classify(claim.text, ev.text,
                            evidence_party=party.get(ev.doc_id, "neutral"), llm=None)
            rel = find.rel if find.rel != "none" else "contradicts"
            hard, mech, expl = find.hard, find.mechanism, find.explanation
            own_goal = find.own_goal
        else:
            rel, hard, mech = "supports", False, ""
            expl = "Evidence corroborates the pleaded point."
            own_goal = False

        if bid not in seen_bundle:
            seen_bundle.add(bid)
            ev_quote = best_quote(claim.text, ev.text)
            if not verbatim_ok(ev_quote, ev.text):
                ev_quote = ev.text
            nodes.append({
                "id": bid, "layer": "claim", "label": ev.text[:42],
                "fulltext": ev.text, "issue": issue_of_prop.get(pid, "PLEADINGS"),
                "polarity": ("legal_overlay" if rel in ("caps", "legal_bar") else "bundle"),
                "source_type": ("legal_clause" if rel in ("caps", "legal_bar") else ev.ev_type),
                "weight": ev.source_strength,
                "verdict": "accepted", "anchor": ev.anchor, "quote": ev_quote,
                "prop": None, "load_bearing": True, "single_source": bool(a.single_source),
                "confidence": a.confidence, "verify": a.verify,
            })
            # provenance: document -> bundle claim
            d = bundle.get(ev.doc_id)
            if d and d.doc_type != "pleading":
                edges.append({
                    "source": f"doc:{ev.doc_id}", "target": bid,
                    "kind": "provenance", "rel": "asserts", "hard": False,
                })
        # coherence: bundle claim -> pleading claim (BUNDLE -> PLEADING)
        edges.append({
            "source": bid, "target": f"claim:{claim.id}", "kind": "coherence",
            "rel": rel, "hard": hard, "explanation": expl, "mechanism": mech,
            "own_goal": own_goal,
        })

    # ---------------------------------------------------------- document nodes
    seen_docs: set[str] = set()
    for tab in sorted(cited_tabs):
        d = bundle.get(tab)
        if d is None or d.id in seen_docs:
            continue
        seen_docs.add(d.id)
        nodes.append({
            "id": f"doc:{d.id}", "layer": "document", "label": d.id,
            "title": d.title, "doc_type": d.doc_type, "party": d.party,
        })

    # ---------------------------------------------------------------- clusters
    clusters = _build_clusters(propositions, claims, assessments, issue_of_prop)

    # ----------------------------------------------------------------- stats
    own_goal = sum(1 for e in edges if e.get("own_goal"))
    rejected = sum(1 for n in nodes
                   if n.get("layer") == "claim" and n.get("polarity") == "pleading"
                   and n.get("verdict") == "rejected")
    readinesses = [n["readiness"] for n in nodes if n.get("layer") == "proposition"]
    pleaded_money = [m for c in claims for m in _money_in(bundle.para_text(c.tab, c.para))]
    supported_money = []
    for pid, a in assessments.items():
        if a.verdict == "SUPPORTED" and pid in claim_by_prop:
            c = claim_by_prop[pid]
            supported_money.extend(_money_in(bundle.para_text(c.tab, c.para)))
    exp_from = _fmt_money(max(pleaded_money)) if pleaded_money else "£0"
    exp_to = _fmt_money(max(supported_money)) if supported_money else exp_from

    stats = {
        "readiness": round(sum(readinesses) / len(readinesses)) if readinesses else 0,
        "own_goal": own_goal,
        "props": len(readinesses),
        "docs": len(seen_docs),
        "claims": sum(1 for n in nodes if n.get("layer") == "claim"),
        "rejected_pleadings": rejected,
        "exposure_from": exp_from, "exposure_to": exp_to,
    }

    # ------------------------------------------------------- documents / index
    # Emit EVERY bundle document (full numbered paragraphs) so the source reader
    # can open any tab — not only the ones a claim happened to cite.
    documents = {}
    for d in sorted(bundle.docs, key=lambda x: x.id):
        documents[d.id] = _doc_entry(d)
    doc_index = [
        {"tab": d.id, "title": d.title, "party": d.party, "date": d.date,
         "category": d.category or _CATEGORY.get(d.doc_type, "Record")}
        for d in sorted(bundle.docs, key=lambda x: x.id)
    ]

    appdata = {
        "meta": {
            "case": meta.get("case", "Case"),
            "claim_no": meta.get("claim_no", ""),
            "court": meta.get("court", ""),
            "seeded": bool(meta.get("seeded", False)),
        },
        "stats": stats,
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "documents": documents,
        "doc_index": doc_index,
        "chronology": chronology if chronology is not None else _chronology(bundle),
    }
    return appdata


def _doc_entry(d) -> dict:
    return {
        "title": d.title, "doc_type": d.doc_type, "party": d.party, "tab": d.id,
        "date": d.date, "category": d.category or _CATEGORY.get(d.doc_type, "Record"),
        "modality": d.modality, "mime": d.mime, "file_url": d.file_url,
        "description": d.description or d.title,
        "paras": [{"n": p.n, "text": p.text} for p in d.paras],
    }


def _chronology(bundle: Bundle) -> list:
    dated = [d for d in bundle.docs if d.date]
    dated.sort(key=lambda d: (d.date, d.id))
    out = []
    for i, d in enumerate(dated, start=1):
        out.append({
            "n": i, "date": d.date,
            "event": f"{d.title} ({d.doc_type}).",
            "evidence": [{"tab": d.id, "para": None}],
            "remarks": "", "source": "ai",
        })
    return out


def _build_clusters(propositions, claims, assessments, issue_of_prop) -> list:
    by_issue: dict[str, list[str]] = {}
    for prop in propositions:
        by_issue.setdefault(issue_of_prop.get(prop["id"], "PLEADINGS"), []).append(prop["id"])

    clusters = []
    for issue in sorted(by_issue):
        pids = by_issue[issue]
        impacts, amendments, story = [], [], []
        n_sup = n_con = n_na = 0
        for pid in pids:
            a = assessments.get(pid)
            verdict = a.verdict if a else "UNVERIFIED"
            overlay = a.legal_risk if a else "NONE"
            impacts.append(f"{pid}: {verdict} [legal overlay: {overlay}]")
            if verdict == "SUPPORTED":
                n_sup += 1
            elif verdict == "CONTRADICTED":
                n_con += 1
                amendments.append(f"Withdraw or re-plead {pid} — contradicted by the bundle.")
            elif verdict == "NOT_ADDRESSED":
                n_na += 1
                amendments.append(f"Add evidence for {pid} — no supporting material found.")
        story.append(f"{issue}: {n_sup} supported, {n_con} contradicted, "
                     f"{n_na} not addressed across {len(pids)} pleaded point(s).")
        clusters.append({
            "issue": issue, "solver": "engine_v2", "story": story,
            "impacts": impacts, "amendments": amendments,
        })
    return clusters
