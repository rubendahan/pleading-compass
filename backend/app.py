"""CMS Pleading-to-Proof — Streamlit UI.

A litigation case-theory stress test, rendered as a dark "law report": a
pleading-to-proof ledger, the case as an evidence/argument graph, contradiction
face-offs, and a cross-examination workbook. Runs offline on the self-test
bundle; point it at the official CMS bundle in data/bundle/ when present.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src import bakeoff, coherence, coverage, ingest, numeric_check, pipeline, pleadings, report  # noqa: E402
from src import graph as graphmod  # noqa: E402
from src.judges import available, get_judge  # noqa: E402

st.set_page_config(page_title="Pleading-to-Proof", layout="wide",
                   initial_sidebar_state="expanded")

# ---------------------------------------------------------------- design tokens
INK = "#101418"
PANEL = "#181D23"
LINE = "#2A313A"
PAPER = "#ECE7DB"
MUTE = "#9AA3AE"
BRASS = "#C8A24A"
VCOL = {"SUPPORTED": "#3FB67A", "CONTRADICTED": "#E0533D",
        "NOT_ADDRESSED": "#8A93A0", "UNVERIFIED": "#5B6470"}
VLABEL = {"SUPPORTED": "Proven", "CONTRADICTED": "Contradicted",
          "NOT_ADDRESSED": "Not addressed", "UNVERIFIED": "Unverified"}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {{ --brass:{BRASS}; --line:{LINE}; --mute:{MUTE}; --panel:{PANEL}; }}
.stApp {{ background:{INK}; }}
.block-container {{ padding-top:2.2rem; max-width:1180px; }}
html, body, [class*="css"] {{ font-family:'IBM Plex Sans',sans-serif; color:{PAPER}; }}
#MainMenu, footer, header {{ visibility:hidden; }}

.eyebrow {{ font-family:'IBM Plex Mono',monospace; font-size:.72rem; letter-spacing:.28em;
  text-transform:uppercase; color:var(--brass); }}
.caption {{ font-family:'Spectral',serif; font-size:2.5rem; line-height:1.05; font-weight:600;
  margin:.1rem 0 .1rem; }}
.caption em {{ font-style:italic; color:var(--brass); }}
.subcap {{ color:var(--mute); font-size:.95rem; margin-bottom:.2rem; }}
.rule {{ height:1px; background:linear-gradient(90deg,var(--brass),transparent); margin:1.1rem 0 1.4rem; }}

.ring {{ width:104px; height:104px; border-radius:50%; display:grid; place-items:center;
  background:conic-gradient(var(--brass) calc(var(--p)*1%), {LINE} 0); }}
.ring > div {{ width:84px; height:84px; border-radius:50%; background:{PANEL}; display:grid;
  place-items:center; text-align:center; }}
.ring b {{ font-family:'Spectral',serif; font-size:1.7rem; line-height:1; }}
.ring span {{ font-size:.6rem; letter-spacing:.12em; color:var(--mute); text-transform:uppercase; }}

.row {{ display:grid; grid-template-columns:118px 1fr 132px; gap:1rem; align-items:start;
  padding:.9rem 0; border-top:1px solid var(--line); }}
.row:last-child {{ border-bottom:1px solid var(--line); }}
.seal {{ font-family:'IBM Plex Mono',monospace; font-size:.7rem; letter-spacing:.06em;
  text-transform:uppercase; padding:.22rem .5rem; border-radius:2px; display:inline-block;
  border:1px solid; font-weight:500; }}
.pid {{ font-family:'IBM Plex Mono',monospace; color:var(--brass); font-size:.8rem; margin-bottom:.25rem; }}
.ptext {{ font-family:'Spectral',serif; font-size:1.06rem; line-height:1.35; }}
.chip {{ font-family:'IBM Plex Mono',monospace; font-size:.72rem; color:{PAPER};
  border:1px solid var(--line); border-left:3px solid var(--mute); padding:.16rem .42rem;
  margin:.3rem .3rem 0 0; display:inline-block; background:#0d1116; }}
.chip small {{ color:var(--mute); }}
.warn {{ color:#E6B450; font-size:.74rem; margin-top:.35rem; }}
.meter {{ height:6px; background:{LINE}; border-radius:3px; overflow:hidden; margin-top:.1rem; }}
.meter > div {{ height:100%; }}
.metnum {{ font-family:'Spectral',serif; font-size:1.15rem; text-align:right; }}
.metlab {{ font-size:.6rem; color:var(--mute); text-transform:uppercase; letter-spacing:.1em; text-align:right; }}

.card {{ background:{PANEL}; border:1px solid var(--line); border-radius:4px; padding:1rem 1.1rem;
  margin-bottom:.8rem; }}
.faceoff {{ display:grid; grid-template-columns:1fr 26px 1fr; gap:.6rem; align-items:center; }}
.faceoff .vs {{ color:var(--brass); text-align:center; font-family:'Spectral',serif; font-style:italic; }}
.quote {{ font-family:'Spectral',serif; font-size:1rem; line-height:1.4; }}
.src {{ font-family:'IBM Plex Mono',monospace; font-size:.72rem; color:var(--mute); margin-bottom:.3rem; }}
mark {{ background:rgba(200,162,74,.28); color:{PAPER}; padding:0 .1rem; border-radius:2px; }}
.cue {{ border-left:3px solid var(--brass); }}
.put {{ font-family:'IBM Plex Mono',monospace; color:var(--brass); font-size:.82rem; }}
.bk td, .bk th {{ font-family:'IBM Plex Mono',monospace; font-size:.82rem; padding:.4rem .7rem;
  border-bottom:1px solid var(--line); text-align:left; }}
.bk th {{ color:var(--mute); text-transform:uppercase; letter-spacing:.08em; font-size:.66rem; }}
h2, h3 {{ font-family:'Spectral',serif !important; font-weight:600; }}
</style>
""", unsafe_allow_html=True)


def esc(s: str) -> str:
    return html.escape(s or "")


def highlight(text: str, quote: str) -> str:
    t, q = esc(text), esc(quote)
    return t.replace(q, f"<mark>{q}</mark>") if q and q in t else t


# ------------------------------------------------------------------- controls
def bundle_options() -> dict[str, str]:
    opts = {"Self-test — Bates v Post Office (synthetic)": str(_ROOT / "data" / "selftest" / "bundle")}
    real = _ROOT / "data" / "bundle"
    if real.exists() and any(p.suffix.lower() in (".md", ".txt", ".pdf", ".docx")
                             and p.name.lower() != "readme.md" for p in real.glob("*")):
        opts["Official CMS bundle — data/bundle/"] = str(real)
    return opts


with st.sidebar:
    st.markdown("<div class='eyebrow'>Case file</div>", unsafe_allow_html=True)
    opts = bundle_options()
    bundle_label = st.selectbox("Bundle", list(opts.keys()))
    side = st.radio("Acting for", ["claimant", "defendant"], horizontal=True)
    judges = available() or ["stub"]
    default_judge = "longcontext" if "longcontext" in judges else judges[0]
    judge_name = st.selectbox("Judge", judges, index=judges.index(default_judge))
    force_stub = st.toggle("Force offline stub", value=True,
                           help="On = deterministic, no API key. Off = real LLM if a key is set.")
    st.caption("Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY to run a real judge.")


bundle = ingest.load_bundle(opts[bundle_label])
props = pleadings.extract_propositions(bundle, force_stub=force_stub)
judge = get_judge(judge_name, force_stub=force_stub)
result = pipeline.analyze(bundle, props, judge, side=side)
props_map = result["props"]
R = result["readiness"]
counts = {"SUPPORTED": 0, "CONTRADICTED": 0, "NOT_ADDRESSED": 0, "UNVERIFIED": 0}
for j in result["judgements"]:
    counts[j["verdict"]] = counts.get(j["verdict"], 0) + 1
case = "Bates v Post Office" if "selftest" in opts[bundle_label] else bundle_label


# --------------------------------------------------------------------- header
head, ring = st.columns([3, 1])
with head:
    st.markdown(
        f"<div class='eyebrow'>Case theory stress test · acting for {esc(side)}</div>"
        f"<div class='caption'>{esc(case.split(' v ')[0])} <em>v</em> "
        f"{esc(case.split(' v ')[-1]) if ' v ' in case else ''}</div>"
        f"<div class='subcap'>{len(props)} pleaded propositions · {len(bundle.docs)} documents · "
        f"backend {esc(result['backend'])}</div>", unsafe_allow_html=True)
with ring:
    st.markdown(
        f"<div class='ring' style='--p:{R['overall']}'><div>"
        f"<b>{R['overall']}</b><span>readiness</span></div></div>", unsafe_allow_html=True)
st.markdown("<div class='rule'></div>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
for col, key in [(m1, "SUPPORTED"), (m2, "CONTRADICTED"), (m3, "NOT_ADDRESSED")]:
    col.markdown(f"<div class='metnum' style='text-align:left;color:{VCOL[key]}'>{counts[key]}</div>"
                 f"<div class='metlab' style='text-align:left'>{VLABEL[key]}</div>", unsafe_allow_html=True)
m4.markdown(f"<div class='metnum' style='text-align:left'>{len(result['contradictions'])}</div>"
            f"<div class='metlab' style='text-align:left'>Contradictions</div>", unsafe_allow_html=True)
st.write("")


# ----------------------------------------------------------------- the ledger
def render_ledger():
    st.markdown("### Pleading-to-proof ledger")
    for j in result["judgements"]:
        pid = j["proposition_id"]
        v = j["verdict"]
        col = VCOL[v]
        text = props_map.get(pid, {}).get("text", "")
        chips = ""
        for e in j["evidence"]:
            chips += (f"<span class='chip' style='border-left-color:{col}'>{e['doc_id']}¶{e['para']}"
                      f" <small>{e['type'].replace('_',' ')} · {e['weight']}</small></span>")
        warn = ("<div class='warn'>⚠ Load-bearing — rests on a single source</div>"
                if j.get("single_source") and v == "SUPPORTED" else "")
        extra = j.get("extra") or {}
        if str(j.get("backend", "")).startswith("panel") and "label" in extra:
            cpct = round(100 * float(j.get("confidence", 0.0)))
            ccol = VCOL["SUPPORTED"] if cpct >= 67 else (VCOL["UNVERIFIED"] if cpct >= 34 else VCOL["CONTRADICTED"])
            dissent = "; ".join(f"{esc(bk)}:{esc(vd)}" for bk, vd in extra.get("dissent", []))
            warn += (f"<div class='warn' style='color:{ccol}'>⚖ panel {esc(extra['label'])} · "
                     f"confidence {cpct}%" + (f" · dissent {dissent}" if dissent else "") + "</div>")
        per = R["per_issue"].get(pid, 0)
        st.markdown(
            "<div class='row'>"
            f"<div><span class='seal' style='color:{col};border-color:{col}'>{VLABEL[v]}</span></div>"
            f"<div><div class='pid'>{pid}</div><div class='ptext'>{esc(text)}</div>{chips}{warn}</div>"
            f"<div><div class='metnum'>{per}</div><div class='metlab'>readiness</div>"
            f"<div class='meter'><div style='width:{per}%;background:{col}'></div></div></div>"
            "</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ the graph
def case_dot() -> str:
    doc_title = {d.id: d.title for d in bundle.docs}
    lines = [
        "digraph G {", "rankdir=LR; bgcolor=\"#101418\";",
        f'node [fontname="IBM Plex Mono" fontsize=10 color="{LINE}" fontcolor="{PAPER}" '
        f'style="filled" fillcolor="#0d1116"];',
        f'edge [color="{MUTE}" penwidth=1.3];',
    ]
    used_docs = set()
    for j in result["judgements"]:
        pid = j["proposition_id"]
        col = VCOL[j["verdict"]]
        lines.append(f'"{pid}" [shape=box style="filled,bold" fillcolor="#181D23" '
                     f'color="{col}" penwidth=2 fontcolor="{PAPER}"];')
        for e in j["evidence"]:
            d = e["doc_id"]
            used_docs.add(d)
            ec = VCOL["SUPPORTED"] if e["polarity"] == "support" else VCOL["CONTRADICTED"]
            lines.append(f'"{d}" -> "{pid}" [color="{ec}"];')
    for d in used_docs:
        t = doc_title.get(d, d)
        short = (t[:22] + "…") if len(t) > 23 else t
        lines.append(f'"{d}" [shape=ellipse label="{d}  {short}"];')
    for c in result["contradictions"]:
        a, b = c["ref_a"].split("¶")[0], c["ref_b"].split("¶")[0]
        lines.append(f'"{a}" -> "{b}" [dir=both style=dashed color="{VCOL["CONTRADICTED"]}" '
                     f'constraint=false];')
    lines.append("}")
    return "\n".join(lines)


# ------------------------------------------------------------------- sections
def render_contradictions():
    cx = result["cross_exam"]
    if not result["contradictions"]:
        st.info("No cross-document contradictions surfaced for this case theory.")
        return
    for c in result["contradictions"]:
        da, pa = c["ref_a"].split("¶"); db, pb = c["ref_b"].split("¶")
        ta = _para_text(da, int(pa)); tb = _para_text(db, int(pb))
        st.markdown(
            "<div class='card'><div class='faceoff'>"
            f"<div><div class='src'>{c['ref_a']} · {esc(_dtitle(da))}</div>"
            f"<div class='quote'>{esc(ta)}</div></div>"
            "<div class='vs'>v</div>"
            f"<div><div class='src'>{c['ref_b']} · {esc(_dtitle(db))}</div>"
            f"<div class='quote'>{esc(tb)}</div></div>"
            f"</div><div class='src' style='margin-top:.6rem;color:{BRASS}'>{esc(c['note'])}</div></div>",
            unsafe_allow_html=True)


def render_crossexam():
    cx = result["cross_exam"]
    if not cx:
        st.info("No cross-examination points for the opponent on this side.")
        return
    for p in cx:
        st.markdown(
            "<div class='card cue'>"
            f"<div class='put'>Put {p['anchor']} to witness {p['put_to']}</div>"
            f"<div class='src' style='margin:.3rem 0'>re [{p['target_prop_id']}] "
            f"{esc(p['target_text'])}</div>"
            f"<div class='quote'>“{esc(p['quote'])}”</div>"
            f"<div class='src' style='margin-top:.4rem;color:{BRASS}'>{esc(p['note'])}</div></div>",
            unsafe_allow_html=True)


def render_risks():
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Gaps to fill")
        if not result["gaps"]:
            st.caption("No unproven propositions on your burden.")
        for g in result["gaps"]:
            st.markdown(
                f"<div class='card'><div class='pid'>{g['prop_id']}</div>"
                f"<div class='ptext' style='font-size:1rem'>{esc(g['prop_text'])}</div>"
                f"<div class='src' style='margin-top:.5rem'>{esc(g['missing'])}</div>"
                f"<div style='margin-top:.4rem;color:{BRASS};font-size:.85rem'>→ {esc(g['suggested_evidence'])}</div>"
                "</div>", unsafe_allow_html=True)
        st.markdown("#### Coverage of the gaps")
        st.caption("Is each absence real, or did we just not look? Every paragraph scored "
                   "against several query variants — the search behind the gap, made verifiable.")
        gap_ids = {g["prop_id"] for g in result["gaps"]}
        gaps_props = [p for p in props if p.id in gap_ids]
        if not gaps_props:
            st.caption("No gaps to probe.")
        for p in gaps_props:
            rep = coverage.coverage_report(p, bundle)
            col = VCOL["NOT_ADDRESSED"] if not rep.crossed else "#E6B450"
            st.markdown(
                f"<div class='card' style='border-left:3px solid {col}'>"
                f"<div class='pid'>{esc(p.id)}</div>"
                f"<div class='src' style='margin-top:.3rem'>{esc(coverage.render_coverage(rep))}</div></div>",
                unsafe_allow_html=True)
    with c2:
        st.markdown("#### Load-bearing evidence")
        if not result["load_bearing"]:
            st.caption("No single-source dependencies.")
        for lb in result["load_bearing"]:
            st.markdown(
                f"<div class='card' style='border-left:3px solid #E6B450'>"
                f"<div class='pid'>{lb['prop_id']} · {lb['anchor']}</div>"
                f"<div class='src' style='margin-top:.3rem'>{esc(lb['risk'])}</div></div>",
                unsafe_allow_html=True)


def render_graph_queries():
    st.markdown("### Evidence graph — the queries a flat matrix can't show")
    st.caption("Propositions ↔ evidence ↔ documents, in a graph. Three signature queries: "
               "your own side's documents sinking your case, pleaded points with no support, "
               "and proofs resting on a single source.")
    own = graphmod.own_goal_contradictions(result, bundle)
    unsup = graphmod.unsupported_propositions(result)
    lb = graphmod.load_bearing_sources(result)

    st.markdown("#### ⚑ Own-goal contradictions")
    st.caption("A pleaded point contradicted by a document from the SIDE THAT PLEADED IT.")
    if not own:
        st.caption("None on this case theory.")
    rcol = VCOL["CONTRADICTED"]
    for o in own:
        st.markdown(
            f"<div class='card' style='border-left:3px solid {rcol}'>"
            f"<div class='pid'>{esc(o['prop_id'])} · contradicted by {esc(o['anchor'])}</div>"
            f"<div class='src' style='margin-top:.3rem'>{esc(o['doc_title'])} ({esc(o['doc_type'])})</div>"
            f"<div class='quote' style='margin-top:.3rem'>“{esc(o['quote'])}”</div></div>",
            unsafe_allow_html=True)

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("#### Absence as a query target")
        st.caption("Pleaded points with no incoming SUPPORTS edge.")
        st.markdown(" ".join(
            f"<span class='chip'>{esc(u['prop_id'])} <small>{esc(u['verdict'])}</small></span>"
            for u in unsup) or "<span class='src'>none</span>", unsafe_allow_html=True)
    with g2:
        st.markdown("#### Load-bearing (single document)")
        st.caption("SUPPORTED points resting on one source.")
        st.markdown(" ".join(
            f"<span class='chip'>{esc(x['prop_id'])} <small>→ {esc(x['doc_id'])}</small></span>"
            for x in lb) or "<span class='src'>none</span>", unsafe_allow_html=True)


def render_numeric():
    st.markdown("### Numeric reconciliation — the solver, not the prose, decides")
    st.caption("Deterministic, offline z3: the case's headline figures, each pleaded value pinned "
               "against the evidenced value. Disjoint tolerance bands ⇒ UNSAT ⇒ contradiction, "
               "citing both anchors. Runs the same with or without an API key.")
    recs = numeric_check.run_numeric_check()
    th = ("<tr><th>quantity</th><th>pleaded</th><th>evidence</th><th>verdict</th>"
          "<th>solver</th><th>legal risk</th></tr>")
    trs = ""
    for r in recs:
        vc = VCOL["CONTRADICTED"] if r.status == "CONTRADICTED" else VCOL["SUPPORTED"]
        p = numeric_check._fmt(r.pleaded, r.unit)
        e = numeric_check._fmt(r.evidence, r.unit)
        trs += (f"<tr><td style='color:{BRASS}'>{esc(r.label)}</td>"
                f"<td>{esc(p)} <small style='color:{MUTE}'>{esc(r.pleaded_anchor)}</small></td>"
                f"<td>{esc(e)} <small style='color:{MUTE}'>{esc(r.evidence_anchor)}</small></td>"
                f"<td style='color:{vc}'>{esc(r.status)}</td><td>{esc(r.solver)}</td>"
                f"<td>{esc(r.legal_risk)}</td></tr>")
    st.markdown(f"<table class='bk'>{th}{trs}</table>", unsafe_allow_html=True)
    cap = numeric_check.cap_analysis()
    st.markdown(
        f"<div class='card cue' style='margin-top:.8rem'><div class='put'>Damages cap</div>"
        f"<div class='src' style='margin-top:.3rem'>{esc(cap['note'])}</div></div>",
        unsafe_allow_html=True)


def render_bakeoff():
    st.markdown("### Judge bake-off — vs the labelled self-test")
    st.caption("Which retrieval/reasoning strategy actually holds up. Real judges (A/B/C/Z3) "
               "need an API key; offline they defer to the stub.")
    rows = bakeoff.run_bakeoff(force_stub=force_stub)
    th = "<tr><th>judge</th><th>accuracy</th><th>P2↔D2</th><th>gaps</th><th>support FP</th>" \
         "<th>anchored</th><th>practitioner</th><th>backend</th></tr>"
    trs = ""
    for r in rows:
        if "error" in r:
            trs += f"<tr><td>{esc(r['name'])}</td><td colspan=7>error: {esc(r['error'])}</td></tr>"
            continue
        acc = f"{int(r['verdict_accuracy']*100)}%"
        yes = lambda b, c=VCOL["SUPPORTED"]: f"<span style='color:{c}'>yes</span>" if b else \
            f"<span style='color:{VCOL['CONTRADICTED']}'>no</span>"
        trs += (f"<tr><td style='color:{BRASS}'>{esc(r['name'])}</td><td>{acc}</td>"
                f"<td>{yes(r['detects_P2_D2'])}</td><td>{r['gaps_correct']}/2</td>"
                f"<td>{r['support_false_pos']}</td><td>{yes(r['anchored_verbatim'])}</td>"
                f"<td>{yes(r['practitioner_output'])}</td><td>{esc(r['backend'])}</td></tr>")
    st.markdown(f"<table class='bk'>{th}{trs}</table>", unsafe_allow_html=True)


def _coh_strength(sol) -> str:
    w = max((c.weight for c in sol.accepted if c.polarity in ("bundle", "legal_overlay")), default=0.0)
    return "strong" if w >= 4 else ("moderate" if w >= 2 else "thin")


def render_coherence():
    st.markdown("### Bundle Coherence — the strongest internally consistent story the bundle supports")
    st.caption("Bundle-first paradigm. Pleading-first checks each pleaded allegation against the "
               "evidence; this asks what coherent story the bundle itself supports, then shows which "
               "pleaded allegations that story rejects or forces the lawyer to amend. "
               "**LLM local, solver global**: a deterministic brute-force max-weight consistency "
               "solver makes the global decision — the LLM never decides truth.")
    st.caption("⚠ Seeded vertical POC over the synthetic Meridian bundle: claims reuse the existing "
               "quote-grounded gold anchors and numeric/graph relations. Paragraph-level LLM "
               "extraction is the future drop-in. Lawyer review required.")

    sols = coherence.analyse(bundle)

    # Summary table
    th = ("<tr><th>Issue</th><th>Rejected / risky pleading</th><th>Suggested amendment</th>"
          "<th>Source strength</th></tr>")
    trs = ""
    for s in sols:
        rej = ", ".join(c.proposition_id or c.id for c in s.rejected if c.polarity == "pleading") or "—"
        amend = esc(s.suggested_amendments[0]) if s.suggested_amendments else "—"
        trs += (f"<tr><td style='color:{BRASS}'>{esc(s.issue)}</td>"
                f"<td style='color:{VCOL['CONTRADICTED']}'>{esc(rej)}</td>"
                f"<td>{amend}</td><td>{esc(_coh_strength(s))}</td></tr>")
    st.markdown(f"<table class='bk'>{th}{trs}</table>", unsafe_allow_html=True)
    st.write("")

    for s in sols:
        story = "".join(f"<div class='src' style='margin:.15rem 0'>· {esc(line)}</div>"
                        for line in s.coherent_story)
        # accepted evidence / legal-overlay chips
        chips = ""
        for c in s.accepted:
            if c.polarity == "pleading":
                continue
            col = BRASS if c.polarity == "legal_overlay" else VCOL["SUPPORTED"]
            anchor = f"{c.source_doc}¶{c.source_para}" if c.source_doc else "no anchor"
            chips += (f"<span class='chip' style='border-left-color:{col}'>{esc(anchor)} "
                      f"<small>{esc(c.source_type.replace('_',' '))} · w{c.weight:g}</small></span>")
        rejected = "".join(
            f"<div class='warn' style='color:{VCOL['CONTRADICTED']}'>✗ [{esc(c.proposition_id or c.id)}] "
            f"{esc(c.text)}</div>" for c in s.rejected if c.polarity == "pleading")
        impacts = "".join(f"<div class='src' style='margin:.2rem 0'>→ {esc(imp)}</div>"
                          for imp in s.pleading_impacts)
        amends = "".join(f"<div style='color:{BRASS};font-size:.85rem;margin:.2rem 0'>✎ {esc(a)}</div>"
                         for a in s.suggested_amendments)
        st.markdown(
            f"<div class='card'><div class='pid'>{esc(s.issue)} · solver: {esc(s.solver)}</div>"
            f"{story}"
            f"<div style='margin-top:.5rem'>{chips}</div>"
            f"{rejected}"
            f"<div style='margin-top:.5rem'>{impacts}</div>"
            f"<div style='margin-top:.4rem'>{amends}</div></div>",
            unsafe_allow_html=True)


def _dtitle(doc_id: str) -> str:
    d = bundle.get(doc_id)
    return d.title if d else doc_id


def _para_text(doc_id: str, n: int) -> str:
    d = bundle.get(doc_id)
    p = d.para(n) if d else None
    return p.text if p else ""


# --------------------------------------------------------------------- layout
render_ledger()
st.write("")
st.markdown("### The case, as a graph")
st.caption("Documents → propositions. Green = supports, red = attacks; dashed red = a pleaded "
           "claim contradicted across documents.")
st.graphviz_chart(case_dot(), width="stretch")
st.write("")

t1, t2, t3, t4, t5, t6, t7 = st.tabs(
    ["Contradictions", "Cross-examination", "Gaps & risks", "Evidence graph",
     "Numeric (Z3)", "Bundle Coherence", "Bake-off"])
with t1:
    render_contradictions()
with t2:
    render_crossexam()
with t3:
    render_risks()
with t4:
    render_graph_queries()
with t5:
    render_numeric()
with t6:
    render_coherence()
with t7:
    render_bakeoff()

st.write("")
st.download_button("Download analysis note (Markdown)", report.render_markdown(result),
                   file_name="case-theory-stress-test.md", mime="text/markdown")
