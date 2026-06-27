"""A1 (`hackthelaw`) phase-2 run  →  the frontend AppData JSON.

Benjamin's backend ("A1", package ``hackthelaw``) emits a *claim-robustness*
analysis as four JSON files in a phase-2 run directory (``claim_reports.json``,
``claims.json``, ``evidence.json``, ``edges.json``) plus a case directory
(``pleading.md`` + a bundle of evidence documents). This module adapts that
output into the exact ``AppData`` shape the React frontend consumes
(``demo/BACKEND-OUTPUT-SPEC.md``), reusing **our** deterministic grounding from
``engine_v2`` (``lexical`` for verbatim quoting / similarity, ``ingest`` for
paragraph splitting). It does **not** import or modify the ``hackthelaw`` package
— it only reads its on-disk artefacts, so it consumes a real phase-2 run
unchanged (same schemas as ``hackthelaw/schemas.py``).

This bridge emits the full-fidelity AppData: ``meta, stats, nodes, edges,
clusters, documents, doc_index, chronology``. The whole bundle is carried — every
evidence document from ``evidence.json`` (plus the pleading at tab ``"02"``)
appears in ``documents`` with its complete numbered paragraphs and in
``doc_index`` — so the source reader / Documents view can open any tab. Only
``sensitivity`` is omitted (the front-end does not render it; the per-node
``load_bearing``/``single_source`` flags it would carry are emitted on the nodes).

Contract obeyed (see the spec):
  * node id prefixes ``prop:`` / ``claim:`` / ``doc:``;
  * anchors ``"<tab>¶<para>"`` (pilcrow U+00B6), ``tab`` == a ``documents`` key;
  * every ``claim.quote`` is a **verbatim substring** of
    ``documents[tab].paras[para].text`` (verified with ``lexical.verbatim_ok``);
  * coherence edges run **BUNDLE → PLEADING** (source = bundle claim, target =
    pleading claim) — the contradiction is carried by the edge;
  * proposition ``verdict`` ∈ {SUPPORTED, CONTRADICTED, NOT_ADDRESSED, UNVERIFIED};
  * ``overlay`` == ``"NONE"`` (A1 has no legal overlays — overlays are sacrificed).

CLI::

    python a1_bridge.py --run <a1_phase2_run_dir> --case <case_dir> --out app_a1.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Reuse OUR grounding (do not reimplement). When run as a script the package
# import needs the prototype root on sys.path.
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine_v2 import ingest, lexical  # noqa: E402

PLEADING_TAB = "02"

# Front-end document `doc_type` enum: contract | pleading | witness | expert |
# record | correspondence.  And the richer `category` enum for the documents map.
_CATEGORY = {
    "pleading": "Pleading", "contract": "Contract", "expert": "Witness (expert)",
    "witness": "Witness (fact)", "correspondence": "Correspondence",
    "record": "Record",
}

# A1 ``Evidence.type``  ->  (source_type vocabulary, doc_type, weight).
# Weight convention (spec §3.5): contracts/signed docs ~5, experts ~4,
# witnesses ~2, emails ~2, else 3.
_SOURCE_PROFILE: dict[str, tuple[str, str, float]] = {
    "contract": ("signed_contract", "contract", 5.0),
    "amendment": ("change_order", "contract", 5.0),
    "change_order": ("change_order", "contract", 5.0),
    "expert_report": ("expert_report", "expert", 4.0),
    "expert": ("expert_report", "expert", 4.0),
    "fact_witness_statement": ("witness_statement", "witness", 2.0),
    "witness_statement": ("witness_statement", "witness", 2.0),
    "witness": ("witness_statement", "witness", 2.0),
    "correspondence": ("contemporaneous_email", "correspondence", 2.0),
    "email": ("contemporaneous_email", "correspondence", 2.0),
    "letter": ("contemporaneous_email", "correspondence", 2.0),
    "record": ("acceptance_certificate", "record", 3.0),
    "internal_record": ("defect_log", "record", 3.0),
    "defect_log": ("defect_log", "record", 3.0),
}

_MONEY = re.compile(r"(?:£|gbp\s*)\s*([\d,]+(?:\.\d+)?)", re.I)
_INT = re.compile(r"\d+")
_HARD_CHALLENGE = 0.6   # a challenging finding at/above this score is decisive


def _source_profile(ev_type: str | None) -> tuple[str, str, float]:
    return _SOURCE_PROFILE.get((ev_type or "").lower(), ("record", "record", 3.0))


# --------------------------------------------------------------------------- IO
def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_run(run_dir: Path) -> dict[str, list]:
    """Read the four phase-2 artefacts. Falls back to the parent dir (phase-2
    *copies* phase-1's claims/evidence/edges, but be resilient if it didn't)."""
    def load(name: str) -> list:
        for cand in (run_dir / name, run_dir.parent / name):
            if cand.exists():
                data = _read_json(cand)
                return data if isinstance(data, list) else []
        return []
    return {
        "reports": load("claim_reports.json"),
        "claims": load("claims.json"),
        "evidence": load("evidence.json"),
        "edges": load("edges.json"),
    }


def _parse_manifest_yaml(path: Path) -> dict:
    """Minimal top-level-scalar reader for A1's ``manifest.yaml`` (no PyYAML dep).

    Only the flat string keys before the ``evidence:`` list are needed
    (``case_name``, ``court``, ``claim_number``, ``case_id``, ``pleading``)."""
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        if not line or line[0] in (" ", "\t", "#", "-"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        if key == "evidence":      # the nested list begins; stop
            break
        val = val.strip().strip("'\"")
        if val and val.lower() != "null":
            out[key] = val
    return out


def _load_meta(run_dir: Path, case_dir: Path, override: dict | None) -> dict:
    """case identity, in priority order: explicit ``meta`` override >
    ``case_manifest.json`` (run/phase0 dir) > case ``manifest.yaml`` > defaults."""
    meta = {"case": "Case", "claim_no": "", "court": "", "seeded": True}

    src: dict = {}
    for cand in (run_dir / "case_manifest.json", run_dir.parent / "case_manifest.json",
                 run_dir.parent.parent / "case_manifest.json",
                 case_dir / "case_manifest.json"):
        if cand.exists():
            try:
                src = _read_json(cand)
                break
            except (OSError, json.JSONDecodeError):
                continue
    if not src:
        src = _parse_manifest_yaml(case_dir / "manifest.yaml")

    if src.get("case_name"):
        meta["case"] = src["case_name"]
    if src.get("claim_number"):
        meta["claim_no"] = src["claim_number"]
    if src.get("court"):
        meta["court"] = src["court"]

    for k, v in (override or {}).items():
        meta[k] = v
    return meta


# ------------------------------------------------------------- paragraphing
def _split_pleading_paras(raw: str) -> list[tuple[int, str]]:
    """Number a Particulars-of-Claim by its **legal** paragraph numbers (so a
    claim's ``paragraph_refs`` index the right text), tolerating the Claim-Form
    preamble + an early "Statement of Truth". Reuses ``engine_v2.ingest``'s
    whitespace reflow; the numbering rule is monotonic ``N.``/``N)`` markers."""
    paras: list[tuple[int, str]] = []
    cur_n: int | None = None
    buf: list[str] = []

    def flush() -> None:
        if cur_n is not None:
            text = re.sub(r"\s+", " ", " ".join(buf)).strip()
            if text:
                paras.append((cur_n, text))

    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^(\d{1,3})[.)]\s*(.+)", s)
        if m and int(m.group(1)) > (cur_n or 0):
            flush()
            cur_n = int(m.group(1))
            buf = [m.group(2)]
        elif cur_n is not None:
            if re.match(r"(?i)^(statement of truth|and the claimant claims)\b", s):
                break
            buf.append(s)
    flush()
    return paras


def _evidence_paras(raw_text: str) -> list[tuple[int, str]]:
    """Split an evidence document's raw text into numbered paragraphs using
    ``engine_v2.ingest`` (blank-line reflow, sequential numbering)."""
    return [(p.n, p.text) for p in ingest._paragraphs(raw_text or "")]


def _best_para(query: str, paras: list[tuple[int, str]]) -> tuple[int, str]:
    """The paragraph most on-point to *query* (deterministic lexical cosine)."""
    best_n, best_text, best_score = paras[0][0], paras[0][1], -1.0
    for n, text in paras:
        score = lexical.similarity(query, text)
        if score > best_score:
            best_n, best_text, best_score = n, text, score
    return best_n, best_text


def _ground_pleading(source_quote: str | None, claim_text: str, p_hint: int | None,
                     paras: list[tuple[int, str]]):
    """Return ``(para_n, verbatim_quote)`` for a pleaded claim, guaranteeing the
    quote is an exact substring of the chosen paragraph."""
    if not paras:
        return None, None
    pmap = {n: t for n, t in paras}
    # 1. the paragraph that verbatim-contains the pleaded source_quote
    if source_quote:
        for n, t in paras:
            if lexical.verbatim_ok(source_quote, t):
                return n, source_quote
    # 2. the paragraph_refs hint
    if p_hint is not None and p_hint in pmap:
        t = pmap[p_hint]
        q = lexical.best_quote(claim_text, t)
        return p_hint, (q if lexical.verbatim_ok(q, t) else t)
    # 3. best lexical match, re-grounded
    n, t = _best_para(source_quote or claim_text, paras)
    q = lexical.best_quote(claim_text, t)
    return n, (q if lexical.verbatim_ok(q, t) else t)


def _ground_evidence(summary: str, paras: list[tuple[int, str]]):
    """Return ``(para_n, verbatim_quote)`` for a bundle finding."""
    if not paras:
        return None, None
    n, t = _best_para(summary, paras)
    q = lexical.best_quote(summary, t)
    return n, (q if lexical.verbatim_ok(q, t) else t)


# ----------------------------------------------------------- verdict mapping
def _first_int(refs) -> int | None:
    for r in refs or []:
        m = _INT.search(str(r))
        if m:
            return int(m.group(0))
    return None


def _scores(findings) -> list[float]:
    out = []
    for f in findings or []:
        s = f.get("score")
        out.append(float(s) if s is not None else 0.0)
    return out


def _decide_verdict(report: dict | None, contradict_edge_score: float | None) -> str:
    """A1 → front-end proposition verdict.

    1. CONTRADICTED — decisive challenging evidence (a challenging finding scored
       ≥0.6, **or** a CONTRADICTS edge from a cited evidence) that outweighs the
       support (its strength ≥ the support strength, or robustness < 50).
    2. SUPPORTED   — verdict == "strong", or robustness ≥ 66 with supporting evidence.
    3. NOT_ADDRESSED — verdict == "unsupported" with no supporting/challenging evidence.
    4. UNVERIFIED  — everything else (asserted but unconfirmed)."""
    if not report:
        return "UNVERIFIED"
    robustness = int(report.get("robustness_score", 0) or 0)
    a1_verdict = (report.get("verdict") or "").lower()
    supporting = report.get("supporting_evidence") or []
    challenging = report.get("challenging_evidence") or []

    chal_scores = _scores(challenging)
    if contradict_edge_score is not None:
        chal_scores.append(contradict_edge_score)
    sup_scores = _scores(supporting) + [robustness / 100.0]

    decisive_challenge = (
        any(s >= _HARD_CHALLENGE for s in _scores(challenging))
        or contradict_edge_score is not None
    )
    max_chal = max(chal_scores or [0.0])
    max_sup = max(sup_scores or [0.0])
    outweighs = max_chal >= max_sup or robustness < 50

    if decisive_challenge and outweighs:
        return "CONTRADICTED"
    if a1_verdict == "strong" or (robustness >= 66 and supporting):
        return "SUPPORTED"
    if a1_verdict == "unsupported" and not supporting and not challenging:
        return "NOT_ADDRESSED"
    return "UNVERIFIED"


# --------------------------------------------------------------------- helpers
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


def _ev_title(ev: dict) -> str:
    desc = (ev.get("description") or "").strip()
    if desc:
        return desc.split(". ")[0][:80]
    base = os.path.basename(ev.get("path") or "") or ev.get("id", "Document")
    return os.path.splitext(base)[0].replace("_", " ")


def _sentences(text: str, k: int = 2) -> list[str]:
    spans = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]
    return spans[:k]


# Finer legal category per A1 ``Evidence.type`` (richer than the coarse doc_type).
_EV_CATEGORY = {
    "contract": "Contract", "amendment": "Amendment", "change_order": "Amendment",
    "expert_report": "Witness (expert)", "fact_witness_statement": "Witness (fact)",
    "witness_statement": "Witness (fact)", "correspondence": "Correspondence",
    "email": "Correspondence", "letter": "Correspondence", "record": "Record",
    "internal_record": "Internal record", "defect_log": "Internal record",
}


def _category_for(ev_type: str | None, doc_type: str) -> str:
    return _EV_CATEGORY.get((ev_type or "").lower(), _CATEGORY.get(doc_type, "Record"))


def _period_start(period: str | None) -> str | None:
    """A1 carries some evidence as a ``period`` ("2024-08-21/2024-08-27"); take
    the start as a sortable date when no single ``date`` is set."""
    if not period:
        return None
    return period.split("/")[0].strip() or None


def _build_chronology(ev_by_id: dict) -> list[dict]:
    """A date-ordered timeline of facts: one concise event per dated evidence
    document, anchored to that tab (paragraph pinned by lexical best-match when a
    body exists, else the whole document). Marked ``source:"ai"`` (LLM-derived)."""
    facts: list[tuple[str, dict]] = []
    for entry in ev_by_id.values():
        ev = entry["ev"]
        date = ev.get("date") or _period_start(ev.get("period"))
        if not date:
            continue
        event = (ev.get("description") or _ev_title(ev)).strip()
        para = None
        if entry["paras"]:
            para, _ = _best_para(event, entry["paras"])
        facts.append((date, {"tab": entry["tab"], "para": para, "event": event}))
    facts.sort(key=lambda kv: (kv[0], kv[1]["tab"]))
    out = []
    for i, (date, f) in enumerate(facts, start=1):
        out.append({
            "n": i, "date": date, "event": f["event"],
            "evidence": [{"tab": f["tab"], "para": f["para"]}],
            "remarks": "", "source": "ai",
        })
    return out


# --------------------------------------------------------------------- main API
def build_appdata(run_dir, case_dir, *, meta: dict | None = None) -> dict:
    """Adapt an A1 phase-2 run directory + its case directory into AppData.

    Emits only the five required keys + the ``documents`` overlay (chronology,
    doc_index and sensitivity are intentionally omitted)."""
    run_dir = Path(run_dir)
    case_dir = Path(case_dir)

    run = _load_run(run_dir)
    reports = run["reports"]
    claims = run["claims"]
    evidence = run["evidence"]
    edges_a1 = run["edges"]

    meta_out = _load_meta(run_dir, case_dir, meta)

    reports_by_id = {r.get("claim_id"): r for r in reports if r.get("claim_id")}

    # CONTRADICTS edges keyed by the evidence they emanate from.
    contradict_from: set[str] = set()
    for e in edges_a1:
        if (e.get("type") or "").upper() == "CONTRADICTS":
            sid = e.get("source_id")
            if sid:
                contradict_from.add(sid)

    # --- pleading text -> legally-numbered paragraphs -----------------------
    manifest = _parse_manifest_yaml(case_dir / "manifest.yaml")
    pleading_name = manifest.get("pleading", "pleading.md")
    pleading_path = case_dir / pleading_name
    pleading_raw = pleading_path.read_text(encoding="utf-8") if pleading_path.exists() else ""
    pleading_paras = _split_pleading_paras(pleading_raw)

    # --- evidence -> per-tab paragraphs -------------------------------------
    ev_by_id: dict[str, dict] = {}
    for ev in evidence:
        tab = ev.get("tab")
        if tab is None:
            continue
        tab_str = f"{int(tab):02d}"
        if tab_str == PLEADING_TAB:           # never shadow the pleading
            continue
        ev_by_id[ev.get("id")] = {
            "ev": ev,
            "tab": tab_str,
            "paras": _evidence_paras(ev.get("raw_text") or ""),
        }

    nodes: list[dict] = []
    edges: list[dict] = []
    clusters: list[dict] = []
    cited_tabs: set[str] = set()
    documents: dict[str, dict] = {}

    # the pleading document (tab "02") is always present
    documents[PLEADING_TAB] = {
        "title": "Particulars of Claim", "doc_type": "pleading", "party": "claimant",
        "tab": PLEADING_TAB, "date": None, "category": "Pleading",
        "modality": "document", "mime": "text/plain", "file_url": None,
        "description": "Particulars of Claim",
        "paras": [{"n": n, "text": t} for n, t in pleading_paras],
    }

    # Number the A1 claims P1..PN by stable claim-id order.
    ordered = sorted(claims, key=lambda c: str(c.get("id")))
    prop_label_by_claim = {c.get("id"): f"P{i}" for i, c in enumerate(ordered, start=1)}

    for c in ordered:
        claim_id = c.get("id")
        plabel = prop_label_by_claim[claim_id]
        issue = plabel
        report = reports_by_id.get(claim_id)
        claim_text = (report or {}).get("claim_text") or c.get("text") or ""
        robustness = int((report or {}).get("robustness_score", 0) or 0)
        supporting = (report or {}).get("supporting_evidence") or []
        challenging = (report or {}).get("challenging_evidence") or []

        # was any cited evidence the source of a CONTRADICTS edge?
        cited = c.get("cited_evidence_ids") or []
        contradict_edge_score = None
        if any(ev_id in contradict_from for ev_id in cited):
            contradict_edge_score = 0.7

        verdict = _decide_verdict(report, contradict_edge_score)
        c_verdict = "accepted" if verdict == "SUPPORTED" else "rejected"
        verify = (verdict in ("NOT_ADDRESSED", "UNVERIFIED")
                  or robustness < 66 or bool(challenging))
        confidence = round(robustness / 100.0, 4)

        # ---- proposition node ----
        prop_node = {
            "id": f"prop:{plabel}", "layer": "proposition", "label": plabel,
            "verdict": verdict, "overlay": "NONE", "readiness": robustness,
            "text": claim_text, "confidence": confidence, "verify": verify,
        }
        if verify:
            prop_node["source"] = "ai"            # -> "AI · verify" badge
        nodes.append(prop_node)

        # ---- pleading claim node ----
        p_hint = _first_int(c.get("paragraph_refs"))
        para_n, quote = _ground_pleading(c.get("source_quote"), claim_text,
                                         p_hint, pleading_paras)
        anchor = f"{PLEADING_TAB}¶{para_n}" if para_n is not None else None
        pleading_claim_id = f"claim:{claim_id}"
        nodes.append({
            "id": pleading_claim_id, "layer": "claim", "label": claim_text[:42],
            "fulltext": claim_text, "issue": issue, "polarity": "pleading",
            "source_type": "pleading", "weight": 1.0, "verdict": c_verdict,
            "anchor": anchor, "quote": quote, "prop": plabel,
            "load_bearing": False, "single_source": len(supporting) == 1,
            "confidence": confidence, "verify": verify,
        })
        # impact edge: pleading claim -> proposition (carries verdict)
        edges.append({
            "source": pleading_claim_id, "target": f"prop:{plabel}",
            "kind": "impact", "rel": "belongs_to", "hard": False, "verdict": c_verdict,
        })

        # ---- bundle claims (one per grounded supporting/challenging finding) ----
        bundle_for_prop: list[dict] = []
        for findings, relation in ((supporting, "supports"), (challenging, "contradicts")):
            for f in findings:
                ev_id = f.get("evidence_id")
                entry = ev_by_id.get(ev_id)
                if entry is None or not entry["paras"]:
                    continue                       # cannot ground -> skip
                ev = entry["ev"]
                tab_str = entry["tab"]
                summary = f.get("summary") or ev.get("description") or ""
                ev_para, ev_quote = _ground_evidence(summary, entry["paras"])
                if ev_para is None:
                    continue
                src_type, doc_type, weight = _source_profile(ev.get("type"))
                bundle_id = f"claim:{claim_id}_{ev_id}"
                score = f.get("score")
                hard = relation == "contradicts" and (score or 0) >= _HARD_CHALLENGE
                ev_party = ev.get("party") or "neutral"

                if not any(n["id"] == bundle_id for n in nodes):
                    nodes.append({
                        "id": bundle_id, "layer": "claim", "label": summary[:42],
                        "fulltext": summary, "issue": issue, "polarity": "bundle",
                        "source_type": src_type, "weight": weight,
                        "verdict": "accepted",        # a real bundle fact stands
                        "anchor": f"{tab_str}¶{ev_para}", "quote": ev_quote,
                        "prop": None, "load_bearing": False,
                        "single_source": False,
                        "confidence": round(float(score), 4) if score is not None else None,
                    })
                    bundle_for_prop.append(
                        {"id": bundle_id, "relation": relation, "weight": weight,
                         "score": score or 0.0})
                    cited_tabs.add(tab_str)
                    # provenance edge: document -> bundle claim
                    edges.append({
                        "source": f"doc:{tab_str}", "target": bundle_id,
                        "kind": "provenance", "rel": "asserts", "hard": False,
                    })
                # coherence edge: BUNDLE -> PLEADING
                verb = "contradicts" if relation == "contradicts" else "corroborates"
                edges.append({
                    "source": bundle_id, "target": pleading_claim_id,
                    "kind": "coherence", "rel": relation, "hard": hard,
                    "own_goal": ev_party == "claimant",
                    "explanation": f"Bundle evidence {verb} the pleaded point: {summary[:140]}",
                })

        # mark the decisive bundle claim load-bearing/single-source per prop
        side = "contradicts" if verdict == "CONTRADICTED" else "supports"
        same_side = [b for b in bundle_for_prop if b["relation"] == side]
        if same_side:
            decisive = max(same_side, key=lambda b: (b["weight"], b["score"]))
            for n in nodes:
                if n["id"] == decisive["id"]:
                    n["load_bearing"] = True
                    n["single_source"] = len(same_side) == 1
            for e in edges:
                if (e.get("kind") == "coherence" and e.get("source") == decisive["id"]
                        and e.get("target") == pleading_claim_id):
                    e["load_bearing"] = e["rel"] == "supports"

        # ---- cluster (one per pleaded point / proposition) ----
        story = _sentences((report or {}).get("legal_explanation", ""), 2)
        action = (report or {}).get("recommended_action", "") or ""
        impacts = [f"{plabel}: {verdict} — {action[:120]}".rstrip(" —")]
        amendments = list((report or {}).get("missing_evidence") or []) + \
            list((report or {}).get("over_extrapolation_risks") or [])
        clusters.append({
            "issue": issue, "solver": "a1_bridge", "story": story,
            "impacts": impacts, "amendments": amendments,
        })

    # -------------------------------------- documents map (the WHOLE bundle)
    # Every evidence document gets a full-paragraph body so the source reader can
    # open any tab (not only the tabs a claim happens to cite).
    for entry in sorted(ev_by_id.values(), key=lambda e: e["tab"]):
        tab_str = entry["tab"]
        ev = entry["ev"]
        _, doc_type, _ = _source_profile(ev.get("type"))
        documents[tab_str] = {
            "title": _ev_title(ev), "doc_type": doc_type, "party": ev.get("party") or "neutral",
            "tab": tab_str, "date": ev.get("date"),
            "category": _category_for(ev.get("type"), doc_type),
            "modality": "document", "mime": "text/plain", "file_url": None,
            "description": ev.get("description") or _ev_title(ev),
            "paras": [{"n": n, "text": t} for n, t in entry["paras"]],
        }

    # --------------------------------------- doc_index (the full bundle spine)
    doc_index = [{
        "tab": PLEADING_TAB, "title": "Particulars of Claim", "party": "claimant",
        "date": None, "category": "Pleading",
    }]
    for entry in ev_by_id.values():
        ev = entry["ev"]
        _, doc_type, _ = _source_profile(ev.get("type"))
        doc_index.append({
            "tab": entry["tab"], "title": _ev_title(ev),
            "party": ev.get("party") or "neutral",
            "date": ev.get("date") or _period_start(ev.get("period")),
            "category": _category_for(ev.get("type"), doc_type),
        })
    doc_index.sort(key=lambda d: d["tab"])

    # ------------------------------------------------------- chronology (facts)
    chronology = _build_chronology(ev_by_id)

    # ------------------------------------------------------------- doc nodes
    # the pleading document node...
    nodes.append({
        "id": f"doc:{PLEADING_TAB}", "layer": "document", "label": PLEADING_TAB,
        "title": "Particulars of Claim", "doc_type": "pleading", "party": "claimant",
    })
    # ...and one per cited evidence tab (graph nodes stay limited to what is wired
    # into the reasoning; the documents map / doc_index carry the full bundle).
    for tab_str in sorted(cited_tabs):
        ev = ev_by_id_by_tab(ev_by_id, tab_str)
        if ev is None:
            continue
        _, doc_type, _ = _source_profile(ev.get("type"))
        nodes.append({
            "id": f"doc:{tab_str}", "layer": "document", "label": tab_str,
            "title": _ev_title(ev), "doc_type": doc_type,
            "party": ev.get("party") or "neutral",
        })

    # ----------------------------------------------------------------- stats
    robustness_all = [int((reports_by_id.get(c.get("id")) or {}).get("robustness_score", 0) or 0)
                      for c in ordered]
    own_goal = sum(1 for e in edges if e.get("own_goal"))
    rejected = sum(1 for n in nodes if n.get("layer") == "claim"
                   and n.get("polarity") == "pleading" and n.get("verdict") == "rejected")
    n_props = sum(1 for n in nodes if n.get("layer") == "proposition")
    n_docs = sum(1 for n in nodes if n.get("layer") == "document")
    n_claims = sum(1 for n in nodes if n.get("layer") == "claim")

    pleaded_money = [m for _, t in pleading_paras for m in _money_in(t)]
    supported_money: list[float] = []
    for c in ordered:
        report = reports_by_id.get(c.get("id"))
        if report and _decide_verdict(report, None) == "SUPPORTED":
            p_hint = _first_int(c.get("paragraph_refs"))
            _, q = _ground_pleading(c.get("source_quote"), c.get("text") or "",
                                    p_hint, pleading_paras)
            supported_money.extend(_money_in(q or ""))
    exp_from = _fmt_money(max(pleaded_money)) if pleaded_money else "—"
    exp_to = _fmt_money(max(supported_money)) if supported_money else (
        exp_from if exp_from != "—" else "—")

    stats = {
        "readiness": round(sum(robustness_all) / len(robustness_all)) if robustness_all else 0,
        "own_goal": own_goal,
        "props": n_props, "docs": n_docs, "claims": n_claims,
        "rejected_pleadings": rejected,
        "exposure_from": exp_from, "exposure_to": exp_to,
    }

    return {
        "meta": meta_out,
        "stats": stats,
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "documents": documents,
        "doc_index": doc_index,
        "chronology": chronology,
    }


def ev_by_id_by_tab(ev_by_id: dict, tab_str: str) -> dict | None:
    for entry in ev_by_id.values():
        if entry["tab"] == tab_str:
            return entry["ev"]
    return None


# --------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Adapt an A1 (hackthelaw) phase-2 run into frontend AppData JSON.")
    ap.add_argument("--run", required=True, help="A1 phase-2 run directory.")
    ap.add_argument("--case", required=True, help="Case directory (pleading + bundle).")
    ap.add_argument("--out", default="app_a1.json", help="Output AppData JSON path.")
    args = ap.parse_args(argv)

    appdata = build_appdata(args.run, args.case)
    Path(args.out).write_text(
        json.dumps(appdata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    s = appdata["stats"]
    print(f"Wrote {args.out}: {s['props']} props, {s['claims']} claims, "
          f"{s['docs']} docs, {len(appdata['edges'])} edges, "
          f"readiness {s['readiness']}/100.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
