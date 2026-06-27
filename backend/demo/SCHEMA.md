# `data.json` — data contract for the Pleading-to-Proof frontend

`python demo/build.py` exports the **real** Meridian analysis to `demo/data.json` (and embeds
the same object in `index.html`). Any frontend (Lovable, React, etc.) can build on this file —
it is the single source of truth. Quotes are loaded verbatim from the bundle and verified;
no value is invented.

Top-level shape:

```jsonc
{
  "meta":   { "case", "claim_no", "court", "seeded" },
  "stats":  { "readiness", "own_goal", "props", "docs", "claims",
              "rejected_pleadings", "exposure_from", "exposure_to" },
  "nodes":  [ ...graph nodes (three layers)... ],
  "edges":  [ ...graph edges (three kinds)... ],
  "clusters":     [ ...one per pleaded issue... ],
  "sensitivity":  [ ...one per pleaded issue... ],
  "documents":    { ...tab id → full document body + metadata... },
  "doc_index":    [ ...every tab in the bundle (lightweight)... ],
  "chronology":   [ ...the agreed/derived timeline... ]
}
```

`meta`, `stats`, `nodes`, `edges`, `clusters` are the core; `sensitivity`, `documents`,
`doc_index`, `chronology` are optional overlays — the frontend degrades gracefully if they are absent.

## Three-layer, claim-centric graph

The reasoning node is the **claim**, never the document. Documents/paragraphs are provenance;
propositions are the litigation target.

```
Document (provenance) ──asserts──▶ Claim (reasoning) ──belongs_to──▶ Proposition (target)
                                    Claim ◀─contradicts/supersedes/caps/…─▶ Claim
```

### `nodes[]`

Common: `id` (e.g. `claim:expert_62`, `doc:19`, `prop:P5`), `layer` ∈ `document | claim | proposition`, `label`.

| layer | extra fields |
|---|---|
| `document` | `title`, `doc_type`, `party` (`claimant`/`defendant`/`neutral`) |
| `claim` | `fulltext`, `issue`, `polarity` (`pleading`/`bundle`/`legal_overlay`), `source_type`, `weight`, `verdict` (`accepted`/`rejected`), `anchor` (`"19¶3"` or null), `quote` (verbatim or null), `prop` (target proposition id or null), `load_bearing` (bool), `single_source` (bool), `blocks` (proposition-claim ids that revive if this claim is removed), `admissibility` (optional — see below) |
| `proposition` | `verdict` (`SUPPORTED`/`CONTRADICTED`/`NOT_ADDRESSED`/`UNVERIFIED`), `overlay` (legal-risk tag or `NONE`), `readiness` (0–100), `text` |

### `edges[]`

`source`, `target` (node ids), `kind` ∈ `provenance | coherence | impact`, `rel`, `hard` (bool).

- `provenance` — `rel: "asserts"`, document → claim.
- `coherence` — `rel ∈ contradicts | supersedes | supports | caps | qualifies | attacks | legal_bar`, claim ↔ claim. `hard` contradictions/supersessions drive the solver. May carry `explanation`, `own_goal` (claimant's own document undermining its pleaded case), `load_bearing`, `blocking`.
- `impact` — `rel: "belongs_to"`, pleading claim → proposition; carries `verdict`.

### `clusters[]` (one per pleaded issue)

`issue`, `solver` (`brute_force`), `story[]` (the coherent narrative), `impacts[]` (per-proposition verdict lines), `amendments[]` (lawyer-facing: withdraw / qualify / reduce / address-cap / add-evidence / reframe).

### `sensitivity[]` (one per pleaded issue)

`issue`, `load_bearing` (pleading-claim id → accepted supporting claim ids), `single_source` (pleading-claim ids resting on exactly one source), `revives_if_removed` (accepted claim id → rejected pleaded points that would revive if it were discredited — the smallest attack).

## Document bodies & indexes (optional overlays)

### `documents` (map: tab id → full document)

Keyed by **tab id** (`"02"`, `"19"`, …). Each value carries verbatim numbered paragraphs plus metadata.
Anchors (`"<tab>¶<n>"`) resolve into `paras` here.

| field | meaning |
|---|---|
| `tab` | the document / tab id (same as the map key, e.g. `"07"`) |
| `title` | document title |
| `doc_type` | legacy type (`contract`/`pleading`/`witness`/`expert`/`record`/`correspondence`) |
| `party` | `claimant`/`defendant`/`neutral` |
| `date` | ISO `yyyy-mm-dd` |
| `category` | `Contract`/`Amendment`/`Correspondence`/`Record`/`Internal record`/`Pleading`/`Witness (fact)`/`Witness (expert)` |
| `modality` | `document`/`email`/`video`/`photo` |
| `mime` | MIME type, e.g. `text/plain` |
| `file_url` | URL to the original file, or `null` |
| `description` | one-line description |
| `paras` | `[{ n, text }]` — verbatim numbered paragraphs |

### `doc_index[]` — every tab in the bundle (lightweight)

`[{ tab, title, party, date, category }]`. Where `documents` holds only the analysed bodies,
`doc_index` lists **all** tabs (e.g. 01–20), so the UI can render the full bundle spine even for tabs
with no extracted body. Same `category` enum as above.

### `chronology[]` — the agreed / derived timeline

`[{ n, date, event, evidence, remarks, source }]`:

| field | meaning |
|---|---|
| `n` | 1-based order |
| `date` | ISO `yyyy-mm-dd` |
| `event` | the fact |
| `evidence` | `[{ tab, para }]` — supporting anchors; `para` is a paragraph number or `null` (whole doc) |
| `remarks` | counsel note (may be `""`) |
| `source` | `counsel` (deterministic) or `ai` (LLM-derived → UI shows "AI · verify") |

### `admissibility` (on a `claim` node)

When a claim rests on evidence with an admissibility issue, the claim node carries an
`admissibility` object: `{ hearsay (bool), personal_knowledge (bool), note (string), source }`,
where `source` is `counsel` (human / deterministic) or `ai` (LLM judgment → "AI · verify").
Omit the whole object when there is no admissibility concern.

## Two views (same graph)

- **Pleading Stress Test** — each proposition traced to its evidence.
- **Bundle Coherence** — the strongest coherent story; rejected pleadings recede.

Colours: `accepted/supported` green `#46C68E`, `rejected/contradicted` red `#E2574A`,
`legal overlay` amber `#E7B45A`, `not addressed/absence` slate `#6A788F`, structural accent
cyan `#3FD3CB`, load-bearing ring brass `#C9A24B`.
