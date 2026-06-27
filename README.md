<div align="center">

# ⚖️ Pleading Compass

**Does your own evidence actually back the case you pleaded?**

A pleading-to-proof stress test for litigation. Feed it a bundle and a pleading, and every pleaded allegation gets checked against the documents: supported, contradicted, or unproven, with the exact source quote behind every call.

Built for the **CMS x Harvey "Pleading-to-Proof"** challenge at Hack the Law 2026.

![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?logo=neo4j&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)

</div>

## What it does

You give it a litigation bundle (contracts, emails, witness statements, expert reports) and the Particulars of Claim. It maps every pleaded proposition to the evidence and surfaces the three things a litigation team usually finds out too late:

- 🟢 what is genuinely **supported**,
- 🔴 what is **contradicted by your own bundle** (the own-goals: a Change Order that quietly moved the go-live date you are suing on, an acceptance certificate that flatly contradicts "we never accepted"),
- ⚪ what has **nothing behind it** yet.

Every verdict is source-linked. Click a node and the document opens at the exact paragraph with the quote highlighted. Nothing is paraphrased into a claim: if a quote is not a verbatim substring of the cited paragraph, it gets dropped.

A few things worth calling out:
- 🗂️ Annotated pleading, an interactive evidence graph, a chronology, and an in-site source reader with the real PDFs.
- 📊 A trial-readiness score and an exposure range (what was pleaded versus what is defensible).
- ⚠️ A VERIFY flag on anything the engine is unsure of, so a lawyer who trusts it blindly is at worst told "check this", never quietly misled.

## How it works

This is a team project with two halves that meet on one JSON contract called **AppData**.

**Front (this repo, `src/`).** A Lovable-built React app (TanStack Start, Vite, Supabase). It renders AppData: nodes (propositions, claims, documents), edges (provenance, coherence, impact), clusters, the full document bodies, and a chronology. The graph uses `react-force-graph-2d`, and the source reader opens the real PDFs.

**Backend (`backend/`).** Two engines, same idea, same output contract.

1. **A1, Benjamin's engine** ([github.com/BenjaminisCoding/Hackthelaw](https://github.com/BenjaminisCoding/Hackthelaw)). It builds a graph of claims and evidence, embeds it, has an LLM read each claim against its evidence, and scores robustness. Run with a strong model (Azure `gpt-5.4`) it reads the case correctly: every own-goal comes back unsupported, every real point comes back strong. The model quality turned out to matter more than anything else.
2. **A2, our engine (`backend/engine_v2`).** Same graph idea, rebuilt with the pieces A1 was missing for this job: paragraph-level retrieval (so the one clause that decides the point actually surfaces), four deterministic contradiction surfacers (numeric mismatch, supersession, contractual allocation, semantic negation), a real CONTRADICTED verdict with legal overlays, and verbatim grounding. It runs on OpenAI and swaps to a local Nemotron with one env change.

**The mapper (`backend/a1_bridge.py`).** A1 emits robustness scores over whole documents. The front needs CONTRADICTED verdicts, legal overlays, and paragraph-anchored verbatim quotes. The mapper bridges the two: it splits documents into numbered paragraphs, re-grounds every finding to a verbatim quote, maps the scores onto our verdict vocabulary, and emits AppData. So Benjamin's backend plugs straight into our front. The complete run is checked in under `backend/pipeline_demo/` (his real gpt-5.4 output, plus our mapped AppData).

```
Benjamin's A1 (gpt-5.4)   ->   a1_bridge mapper        ->   AppData   ->   Pleading Compass
   or our A2 engine            (paragraph anchors,                          (this repo)
                                verbatim quotes,
                                contradiction verdicts)
```

## The two cases

- **Meridian Retail v TechFlow.** The official CMS synthetic bundle, 21 documents. A claimant whose own bundle sinks half of its pleaded case.
- **Brightmarket v Cobalt.** A GDPR dispute we wrote ourselves, with seven traps planted on purpose: a clause that reads like a warranty until the next line, a figure that looks consistent until you check the unit, an impossible chronology, a three-document inference that breaks at every link, a superseded draft clause, a genuinely ambiguous claim that must be flagged rather than answered, and a duty that sits with the other party. The point was to check that the engine catches them, or at least flags them, instead of waving them through.

## Results

| | |
|---|---|
| Meridian, verified benchmark | 13 / 13 propositions |
| Meridian, full A1 pipeline (gpt-5.4) through our mapper | every own-goal flagged CONTRADICTED |
| Brightmarket, 7 planted traps | all caught or flagged, none waved through |
| Safety invariant, both cases | 0 contradicted points marked supported at high confidence |

The benchmark cases shipped in the app are the human-verified ground truth. The live A1 pipeline with a strong model reproduces the headline calls on its own. The lesson we kept relearning: with a capable LLM the reasoning is solid, and the work that makes it usable by a lawyer is the paragraph grounding and the verdict mapping on top.

## Running it

Front:
```bash
npm install
npm run dev
```

Backend (Python 3.13):
```bash
cd backend
pip install -r requirements.txt

# our A2 engine, instant and deterministic, no key needed
python -m engine_v2.cli run --pleading data/bundle/02_Particulars_of_Claim.docx \
       --bundle data/bundle --out app.json --offline

# our A2 engine, live, using OpenAI
export OPENAI_API_KEY=sk-...
python -m engine_v2.cli run --pleading <pleading> --bundle <dir> --out app.json

# Benjamin's A1 output through our mapper (the full pipeline)
python a1_bridge.py --run pipeline_demo/benjamin_a1_gpt54 --case <cms_synthetic> --out app.json
```

Swapping GPT for a local NVIDIA Nemotron is an env change, not a rewrite: point `OPENAI_BASE_URL` at a local OpenAI-compatible server and set `LLM_MODEL`. Set `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` to push the evidence graph to Neo4j. More in `backend/A2-BACKEND.md`.

## Guarantees

- Every quote is a verbatim substring of its cited paragraph, or it is dropped. No invented sources.
- Every pleaded paragraph gets an explicit status. A silent blank is impossible by construction.
- A calibrated confidence and a VERIFY flag, so uncertainty is shown rather than hidden.

## The method, in 15 slides

`backend/docs/methods.pdf` walks through the whole approach, the tools, the guarantees, and the lawyer value, grounded in our team lawyer's own annotated read of the case.

## Credits

A Hack the Law 2026 team project for the CMS x Harvey "Pleading-to-Proof" challenge.

- Backend reasoning engine (A1): **Benjamin**, [Hackthelaw](https://github.com/BenjaminisCoding/Hackthelaw).
- Frontend, the A2 engine, the mapper, and the EU stress-test cases: **Ruben**.
- Tools: OpenAI for reasoning and embeddings, Neo4j AuraDB for the evidence graph, Lovable for the frontend.
