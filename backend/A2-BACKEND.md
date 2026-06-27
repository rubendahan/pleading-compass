# A2 — the live Pleading-to-Proof backend (`engine_v2`)

Our shipped method. Systematic, raw documents → the `AppData` JSON the **Pleading Compass**
front renders. Benjamin's A1 graph idea, rebuilt with **paragraph-split + contradiction
surfacers + verbatim grounding**. (The old `coherence.py` only renders the hand-verified
**gold benchmark** — it is not the engine.)

## Pipeline (7 steps)
1. Split every document into **numbered paragraphs** (enables clause-level retrieval + verbatim anchors).
2. Extract the pleaded propositions from the pleading.
3. Embed + retrieve top-K paragraphs per proposition (OpenAI embeddings, or instant local).
4. Detect contradictions: **deterministic surfacers** (numeric-disjoint, supersession,
   contractual-allocation, semantic-negation) **+ an LLM classifier** (OpenAI). Only a
   *grounded* contradiction flips a point; strong corroboration beats an LLM guess.
5. Verdict (SUPPORTED / CONTRADICTED / NOT_ADDRESSED / UNVERIFIED) + legal overlay +
   calibrated **confidence** + a **VERIFY** flag.
6. **Ground every quote verbatim** — non-verbatim quotes are dropped, never invented.
7. Emit `AppData` (meta, stats, nodes, edges, clusters, documents-with-paragraphs, doc_index, chronology).

## Run it

```bash
# instant, deterministic (no key, no network) — the safe demo path
python -m engine_v2.cli run --pleading data/bundle/02_Particulars_of_Claim.docx \
       --bundle data/bundle --out app.json --offline

# live, using the tools (OpenAI LLM + embeddings)
export OPENAI_API_KEY=sk-...
python -m engine_v2.cli run --pleading <pleading> --bundle <dir> --out app.json
#   add ENGINE_FORCE_LOCAL_EMBED=1 for instant lexical retrieval + OpenAI reasoning (fast)

# serve it for the frontend
python -m engine_v2.server            # POST /analyze  ->  AppData   (host/port from env)
```

## Plug it into the Lovable site
The front (`pleading-compass`) already has the seam: its **Re-analyze** action POSTs the
bundle to `process.env.ENGINE_URL` `/analyze` and renders the returned `AppData`.

```bash
# in the front's environment
ENGINE_URL=http://127.0.0.1:8000      # where `python -m engine_v2.server` is listening
```
Run the front + the engine locally and "Re-analyze" calls A2. The curated benchmark cases
(`demo-case.json`, `eu-case.json`) stay loaded and accessible regardless.

## Swap GPT → local NVIDIA Nemotron (no code change)
The LLM seam (`engine_v2/llm.py`) talks the OpenAI protocol and reads the base URL + model
from the environment. Point it at any OpenAI-compatible local server (vLLM / TGI / Ollama)
running Nemotron:

```bash
export OPENAI_BASE_URL=http://localhost:8001/v1   # your local Nemotron endpoint
export LLM_MODEL=nemotron-nano                     # the local model id
export OPENAI_API_KEY=local                        # dummy; local servers ignore it
```
GPT is unplugged, Nemotron is plugged in. (Embeddings similarly via `EMBED_MODEL`, or use
the instant local embedder with `ENGINE_FORCE_LOCAL_EMBED=1`.)

## Neo4j (the evidence graph tool)
Set `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` to persist the claim/evidence graph to AuraDB.

## Guarantees & accuracy
- **Anti-hallucination:** every quote is a verbatim substring of its cited paragraph;
  **coverage guarantee** (every pleaded paragraph gets an explicit status — no silent blanks);
  calibrated confidence + a VERIFY flag so the lawyer is, at worst, told "verify this".
- **Safety invariant:** never marks a contradicted/planted-false point SUPPORTED at high
  confidence (0 such errors on both datasets); every miss is flagged VERIFY.
- **Benchmark vs live:** the curated benchmark is 13/13 on Meridian (human-verified ground
  truth, shown in the demo). The live systematic engine is rougher on adversarial cases and
  **flags what it is unsure of** rather than guessing.
