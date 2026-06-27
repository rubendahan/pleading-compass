# ⚖️ CMS Pleading-to-Proof — case theory stress test

Hack the Law 2026, **CMS** track (*Pleading-to-Proof: AI Case Theory Stress Test*).

Take a litigation bundle, take each **pleaded proposition** (allegation / defence), and
stress-test the case theory: is it **🟢 proven · 🔴 contradicted · ⚪ not addressed** — with
**source-anchored verbatim evidence** (doc ¶), cross-document **contradictions**, and the things a
litigator actually does next: **cross-examination points**, **gaps to fill**, **load-bearing
evidence** (single points of failure), all **side-aware** (acting for claimant vs defendant).

> Runs **offline with no API key** on a labelled self-test bundle anchored on *Bates v Post Office*
> [2019] EWHC 3408. Drop the official CMS *Post Office Witness Statements* into `data/bundle/` to run
> on the real thing.

## How it works

```
ingest (bundle/) → propositions → [ pluggable JUDGE ] → report (matrix + practitioner views)
                                         ↑ A | B | C | Z3            ↑ app.py (Streamlit) · cli.py
```

- **`ingest`** — a folder of documents → `Bundle`. `.md`/`.txt` now; `.pdf` (pdfplumber + OCR
  fallback) and `.docx` for the real bundle. Paragraphs are numbered → stable `doc ¶n` anchors.
- **Judge** (pluggable, behind one interface) — classifies a proposition against the bundle:
  - **A `longcontext`** — reads the *whole* bundle, no retrieval (stacks Nemotron 1M). Most faithful
    for contradiction + absence.
  - **B `rag`** — lexical top-k retrieval. Kept to *show* how RAG misses a contradiction that isn't
    lexically near, or hallucinates support on a gap.
  - **C `argument`** — LLM extracts a Toulmin/Dung claim graph (grounds/rebuttals); the verdict is
    *derived from the graph* → explainable, anti-"just RAG".
  - **Z3 `numeric`** — SMT consistency of numeric/temporal facts (£x vs ledger £y). Narrow, high-precision.
  - **`stub`** — deterministic offline judge so everything runs with no key.
- **`report`** — the pleading-to-proof matrix, **per-issue + overall trial-readiness**, and the
  practitioner views (cross-exam, gaps→remedy, load-bearing); Markdown analysis-note export.
- **`bakeoff`** — scores every judge against the labelled self-test GOLD (verdict accuracy, does it
  catch the cross-doc contradiction, does it flag the gaps, support false-positives, verbatim
  anchoring, practitioner output).

## Run it

```powershell
cd prototypes\cms-pleading-proof
py -3 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py            # the UI (self-test, offline, no key needed)
```

CLI:

```powershell
python -m src.cli --side claimant                 # analyse the self-test bundle (stub)
python -m src.cli --side claimant --markdown       # the analysis note
python -m src.cli --bakeoff                         # compare all available judges
python -m src.cli --bundle data\bundle --judge longcontext --side claimant   # real bundle + real LLM
```

Real LLM (free): an `OPENROUTER_API_KEY` (Nemotron) or `ANTHROPIC_API_KEY` in the environment, then
turn off "Force offline stub" in the UI (or drop `--stub`).

## What's live offline vs needs a key

- **Live now (no key):** ingestion, proposition seeding, the stub judge, the full pipeline,
  practitioner views, the bake-off scorer, and the whole UI — on the labelled self-test bundle.
- **Needs a key:** the LLM judges A/B/C and the Z3 fact-extraction (wiring verified to the 401
  boundary; the network call is not exercised without a key).
- **Needs the official bundle:** `data/bundle/` — the real *Post Office Witness Statements*; the real
  answer key is then built with a legal teammate.

## The self-test, honestly

`data/selftest/` is a small, deliberately conflicting bundle (Particulars, Defence, two witness
statements, an expert report, an internal email) with a GOLD answer key. It validates the scorer on
labels we know — you can only trust a bake-off on labelled data. The real de-risk is running on the
official bundle.
