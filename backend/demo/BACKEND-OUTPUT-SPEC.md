# BACKEND-OUTPUT-SPEC.md - exactly what the analysis engine must emit

Audience: Benjamin (and his Codex/coding agent). Scope: the **analysis backend** - the
LLM/engine that turns a litigation bundle into one case's data. This document does **not**
cover the website (auth, accounts, Supabase, routing). It defines only the JSON the engine
produces and that the frontend reads.

Source of truth, in priority order:

1. `pleading-compass/src/lib/pleading.ts` - the `AppData` TypeScript type (canonical shape + enums).
2. `demo/data.json` - the full worked example (Meridian v TechFlow). Exact shapes/enums confirmed here.
3. The frontend components (what each field actually drives on screen).
4. `demo/SCHEMA.md` and `demo/INTEGRATION.md` - the existing contract docs this file extends and aligns with (it does not contradict them).

---

## 1. TL;DR (read this, then skim the rest)

- The backend emits **one JSON document per case** in the `AppData` shape (`demo/data.json` is a complete example). Deliver it by URL/endpoint (`GET` → the object, CORS-enabled) or as a stored case record.
- **Five required top-level keys**: `meta`, `stats`, `nodes`, `edges`, `clusters`. The frontend will not render a case without them.
- **Four optional overlays**: `sensitivity`, `documents`, `doc_index`, `chronology`. Each one lights up a screen/affordance; if absent, that affordance simply hides.
- **Golden rule**: *emit what you can, omit the rest - the UI degrades gracefully.* A missing `quote`, `readiness`, `chronology`, or `documents` map just removes one affordance. Never block on completeness.
- **The one hard rule**: **every `quote` must be a verbatim substring of the exact paragraph it cites** (`documents[tab].paras[n].text`). The verify dialog highlights the quote by `text.indexOf(quote)`; if it is not a literal substring, the highlight silently fails and the lawyer's trust path breaks. **Never invent a source, a quote, or an anchor.**
- **Mark anything an LLM judged** with `source: "ai"` (chronology facts) or `…source: "ai"` (admissibility / a proposition's verdict provenance) so the UI badges it "AI · verify". Deterministic/counsel items use `"counsel"` or omit `source`.
- **Vocabularies (exact):**
  - node `layer`: `document` · `claim` · `proposition`
  - proposition `verdict`: `SUPPORTED` · `CONTRADICTED` · `NOT_ADDRESSED` · `UNVERIFIED`
  - proposition `overlay`: `NONE` · `CONTRACTUALLY_BARRED` · `SUPERSEDED` · `CAPPED` · `CAUSATION_PROBLEM` · `BURDEN_PROBLEM`
  - claim `verdict`: `accepted` · `rejected`
  - claim `polarity`: `pleading` · `bundle` · `legal_overlay`
  - edge `kind`: `provenance` · `coherence` · `impact`
  - edge `rel`: `asserts` · `contradicts` · `supersedes` · `supports` · `caps` · `qualifies` · `attacks` · `legal_bar` · `belongs_to`
- **Node id prefixes**: `prop:` · `claim:` · `doc:`. **Anchor format**: `"<tab>¶<para>"` (e.g. `"19¶3"`), where `tab` == the document/`doc:` id.

---

## 2. What the site does with it (why each field exists)

The case page (`routes/_authenticated/cases.$caseId.tsx`) has three switchable views - **Pleading**,
**Chronology**, **Graph** - plus an on-demand **Inspector** drawer and an in-context **verify** dialog.
Here is exactly which fields each surface reads.

### 2.1 Header - the three stat chips (always visible)

Rendered top-right of every view. Each is a small two-line chip (label + value):

| Chip label | Value shown | Field(s) read | Colour logic |
|---|---|---|---|
| `trial readiness` | `{readiness}/100` | `stats.readiness` | ≥70 green, ≥30 amber, else red |
| `own goals` | `{own_goal}/10` | `stats.own_goal` | always orange |
| `exposure` | `{exposure_from} to {exposure_to}` | `stats.exposure_from`, `stats.exposure_to` | always ink (black) |

The header title/subtitle (case name, claim no, court) is taken from the **case record** (`row.title`,
`row.claim_no`, `row.court`) - a website concern - but you should mirror those in `meta` so the
pleading view's document head matches.

### 2.2 View switcher

Three buttons: **Pleading** · **Chronology** · **Graph**. (A fourth dual-pane "stress" layout exists in
code but is not on the toggle.) No backend field selects the view; it is UI state.

### 2.3 Pleading view (the hero - `AnnotatedPleading.tsx`)

Renders `documents["02"]` (the Particulars of Claim) as a legal document, one numbered paragraph per
row, with **counsel-style margin notes**:

- The pleaded text comes from `documents["02"].paras[]` (`n`, `text`).
- A margin note attaches to paragraph `n` for every **pleading** claim whose `anchor` is `"02¶n"`. From that claim's `prop` field it resolves the target proposition `prop:{prop}`.
- The note shows `{proposition.label} · {verdict phrase}` (e.g. "P2 · Contradicted by evidence"), coloured by the proposition `verdict`, plus a `TrustBadge` driven by the proposition's optional `source`.
- The **controlling-evidence** line (`Tab 4 · ¶9  [verify]`) is computed by `controllingEvidence()`: among **coherence** edges whose **target is this pleading claim**, it picks the highest-ranked one whose **source is a non-pleading claim**, and surfaces that source claim's `anchor` + `quote`. Rank = `REL_RANK[rel]*100 + source.weight` (contradicts/supersedes rank highest).
- If the proposition is `NOT_ADDRESSED` and there is no controlling evidence, it prints "No supporting evidence in the bundle."
- A non-`NONE` `overlay` renders an amber "legal · …" tag.
- If `documents["02"]` is absent, it falls back to listing proposition nodes directly (`PropositionFallback`).

### 2.4 Verify dialog (`SourceReader.tsx`) - opens from any anchor button

- Parses the anchor `"<tab>¶<para>"`, looks up `documents[tab]`.
- If the document has `file_url` → `FileViewer` renders the real file (image / video / iframe-PDF, chosen by `mime`) with the quote shown alongside.
- Otherwise → `Reader` lists `paras[]`, scrolls to paragraph `para`, and **highlights `quote`** inside that paragraph's `text` via `indexOf`. This is why the quote must be verbatim.
- The `doc_type` and `party` chips at the top come from `documents[tab]`.

### 2.5 Chronology view (`Chronology.tsx`) - two tabs

- **Facts** tab reads `chronology[]`: each fact shows `date`, `event`, one verify-button per `evidence[{tab,para}]`, a `TrustBadge` on `source`, and optional `remarks`.
- **Documents** tab reads `doc_index[]` (sorted by `date`): a table of `Tab` (`tabLabel`), `Document` (`title`), `Date`, `Category`, `Party`.

### 2.6 Graph view (`GraphCanvas.tsx`)

Force-directed three-layer graph. Reads `nodes` and `edges`:

- **Node shape**: documents = squares, claims/propositions = circles.
- **Node colour** (`nodeColor`): proposition → by `verdict`; claim → by `verdict`, except `polarity:"legal_overlay"` → amber; document → ink accent.
- **Node radius** = importance: proposition fixed; document grows with edge-degree; claim grows with `weight` (+ a bump if `load_bearing`).
- **load_bearing** nodes get a brass ring and are always labelled.
- **Edge colour/width** (`edgeColor`): by `rel`; `hard:true` edges draw thicker; `asserts` draws thin/dashed; `belongs_to` draws as a tight pull with no arrow.
- Labels declutter by zoom; load-bearing claims, heavy claims (`weight≥4`) and well-connected documents stay labelled.

### 2.7 Inspector drawer (`Inspector.tsx`) - opens on selecting a node or edge

- **Proposition**: `VerdictPill(verdict)`, `OverlayChip(overlay)`, `text`, `ReadinessBar(readiness)`, a **Controlling evidence** card (the most decisive targeting claim: verifiable→load-bearing→heaviest, with `fulltext`, `quote`, verify button), a plain-language **Why** (from the matching `clusters[].impacts` line, else `clusters[].story[0]`), and a collapsible **Analysis** (coherent `story`, claims targeting this prop, suggested `amendments`).
- **Claim**: `VerdictPill`, `load-bearing`/`single source` flags, `polarity · source_type · weight`, `fulltext`, the **verbatim quote** block (✓ verbatim badge + verify button), an **If discredited … would revive** line from `blocks`, **Source** (provenance docs), and **Coherence relations** (with `explanation` and an "own goal" tag).
- **Document**: `doc_type` / `party` / `doc {label}` chips, `title`, and the claims it asserts.
- **Edge**: `rel` pill, `kind`, `hard`, `own_goal`, From/To node cards, and `explanation`.
- The **Note** panel ("generate") calls a live server function (`summariseNode`) - that is a website concern, **not** part of this JSON. You do not emit it.

---

## 3. Complete field reference

Legend for columns: **Req** = required (R) / optional (O); **By** = Deterministic (D, mechanical/countable) or LLM-judged (L). "UI" names the surface that reads it (§2).

### 3.0 Top-level keys

| Key | Type | Req | Notes |
|---|---|---|---|
| `meta` | object | R | Case identity. |
| `stats` | object | R | Header counters. |
| `nodes` | array | R | Three-layer graph nodes. |
| `edges` | array | R | Relationships. |
| `clusters` | array | R | One per pleaded issue. May be `[]`. |
| `sensitivity` | array | O | One per issue; load-bearing / single-source / revives map. |
| `documents` | object (map) | O | tab id → full document body + metadata. |
| `doc_index` | array | O | Every tab (lightweight spine). |
| `chronology` | array | O | The timeline of facts. |

### 3.1 `meta`

| Field | Type | Req | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `case` | string | R | - | D | Pleading head (italic case name) | Full case caption, e.g. `"Meridian Retail Group plc  v  TechFlow Solutions Ltd"`. |
| `claim_no` | string | R | - | D | Pleading head ("Claim …") | Court claim number, e.g. `"HT-2025-000231"`. |
| `court` | string | R | - | D | Pleading head (top line) | e.g. `"Technology and Construction Court"`. |
| `seeded` | boolean | O | `true`/`false` | D | not rendered | Provenance flag (synthetic/seeded vs real). Carry it; no visible effect. |

### 3.2 `stats`

`exposure_from`/`exposure_to` are **pre-formatted display strings** - the UI prints them verbatim, so
do the currency formatting here. Convention: `exposure_from` = the **as-pleaded headline** exposure
(higher), `exposure_to` = the **defensible** figure after coherence + caps (lower).

| Field | Type | Req | By | UI | How to derive |
|---|---|---|---|---|---|
| `readiness` | number `0–100` | R | L/D | Header chip "trial readiness"; colour 70/30 thresholds | Case-level trial-readiness score. Roll up from proposition `readiness` (e.g. evidence-backed share of pleaded value). |
| `own_goal` | number | R* | D | Header chip "own goals" (`/10`) | Count of coherence edges with `own_goal:true` (claimant's own material undermining its case). |
| `exposure_from` | string | R* | D | Header chip "exposure" (left of "to") | Headline pleaded exposure, formatted, e.g. `"£6.0m"`. |
| `exposure_to` | string | R* | D/L | Header chip "exposure" (right of "to") | Defensible exposure after rejected pleadings + caps, e.g. `"£1.8m"`. |
| `props` | number | O | D | not read | Count of `proposition` nodes. Emit for parity with `data.json`. |
| `docs` | number | O | D | not read | Count of `document` nodes. |
| `claims` | number | O | D | not read | Count of `claim` nodes. |
| `rejected_pleadings` | number | O | D | not read | Count of `pleading` claims with `verdict:"rejected"`. |

\* `own_goal`, `exposure_from`, `exposure_to` are not type-required, but the header chips print them
directly - omit them and the chip shows `undefined`. Treat them as required for a clean header.

### 3.3 `nodes[]` - common fields (all layers)

| Field | Type | Req | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `id` | string | R | prefixed `prop:` / `claim:` / `doc:` | D | every lookup; edge endpoints | Unique node id. `doc:` id == the tab id (`doc:07` ↔ tab `"07"`). |
| `layer` | string | R | `document` · `claim` · `proposition` | D | dispatch everywhere | Which layer this node is. |
| `label` | string | R | - | D | graph labels, chips, inspector headings | Short label. Propositions: `"P1"`, `"P9a"`. Documents: the tab id (`"07"`). Claims: a short truncation of the claim (free text). |

### 3.4 `proposition` node (the litigation target - what is pleaded)

One per pleaded allegation. `verdict`/`overlay`/`readiness` are the analytic outputs.

| Field | Type | Req | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `verdict` | string | R | `SUPPORTED` · `CONTRADICTED` · `NOT_ADDRESSED` · `UNVERIFIED` | L | margin-note phrase + colour; `VerdictPill`; graph colour; scroll ranking | The coherence outcome for the allegation. `SUPPORTED` survives; `CONTRADICTED` is beaten by the bundle; `NOT_ADDRESSED` has no bundle evidence either way; `UNVERIFIED` = asserted but unconfirmed. |
| `overlay` | string | R | `NONE` · `CONTRACTUALLY_BARRED` · `SUPERSEDED` · `CAPPED` · `CAUSATION_PROBLEM` · `BURDEN_PROBLEM` | L | amber "legal · …" tag (margin + `OverlayChip`) | Legal-risk overlay independent of the factual verdict. Use `"NONE"` when there is none (do not omit). |
| `readiness` | number `0–100` | R | - | L/D | `ReadinessBar` (colour 70/30) | Per-allegation trial readiness. 100 for clean SUPPORTED, 0 for rejected/blocked, mid-range for qualified. |
| `text` | string | R | - | D | margin fallback, inspector body, graph | The full pleaded allegation, in plain prose. |
| `source` | string | O | `"ai"` / `"model"` → "AI · verify"; else "from source" | - | `TrustBadge` in the margin note | Tag the verdict's provenance. Set `"ai"` if the verdict is an LLM judgment you want flagged for human check; omit (or `"counsel"`) if deterministic/reviewed. *(Not in the TS interface but read via `prop.source`.)* |

### 3.5 `claim` node (the reasoning unit - atomic, quote-grounded)

The reasoning node is the **claim**, never the document. Three polarities: a `pleading` claim restates
one pleaded point; a `bundle` claim is a quote-grounded fact from the evidence; a `legal_overlay` claim
is a contractual bar/cap.

| Field | Type | Req | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `fulltext` | string | R | - | L | inspector body, controlling-evidence card, claim rows, graph label | The full claim sentence (one atomic proposition). |
| `issue` | string | R | free text, but **must match a `clusters[].issue`** | L | links claim → its cluster (inspector "Why"/Analysis) | The pleaded-issue bucket, e.g. `"DELAY/SCOPE"`, `"ACCEPTANCE"`, `"QUANTUM/CAP"`. Use a stable UPPER/slash token shared by every claim + cluster on that issue. |
| `polarity` | string | R | `pleading` · `bundle` · `legal_overlay` | L | colour (legal_overlay→amber); controlling-evidence filter; margin mapping | `pleading` = the allegation as pleaded; `bundle` = evidence-grounded; `legal_overlay` = legal bar/cap. |
| `source_type` | string | R | free text (see list) | L | shown (`_`→space) in claim view/rows; sets weight | The kind of source. Observed values: `pleading`, `signed_contract`, `change_order`, `legal_clause`, `acceptance_certificate`, `defect_log`, `contemporaneous_email`, `witness_statement`, `expert_report`, `absence`. |
| `weight` | number | R | - | D/L | controlling-evidence ranking; graph radius; key-label threshold (`≥4`); inspector tiebreak | Source strength. Convention: contracts/signed docs ~`5`, experts ~`4`, witnesses ~`2`, pleadings `1.0`, bare `absence` `1.0`. |
| `verdict` | string | R | `accepted` · `rejected` | L | colour; `VerdictPill`; impact-edge verdict | Whether the claim survives coherence. A pleaded point beaten by the bundle is `rejected`; a corroborated bundle fact is `accepted`. |
| `anchor` | string \| null | R (nullable) | format `"<tab>¶<para>"` | D | verify button; **margin mapping (`02¶n`)**; highlight target | Where the quote lives. `tab` == a `documents` key / `doc:` id. `null` only when there is no source (e.g. an `absence` claim). |
| `quote` | string \| null | R (nullable) | - | L (extractive) | blockquote + highlight in verify dialog | **Verbatim substring** of `documents[tab].paras[para].text`. `null` if no quote. Must satisfy `paraText.indexOf(quote) >= 0`. Never paraphrase. |
| `prop` | string \| null | R (nullable) | a proposition label **without** the `prop:` prefix (e.g. `"P2"`) | D | margin mapping (`prop:{prop}`); inspector grouping | Set on **pleading** claims only - the allegation this claim is pleaded to. `bundle`/`legal_overlay` claims → `null`. |
| `load_bearing` | boolean | R | - | D/L | brass ring + flag; ranking; key labels | `true` if this claim is the sole/decisive support of a surviving point (discredit it and the point falls). |
| `single_source` | boolean | R | - | D | "single source" flag | `true` if the claim rests on exactly one source. |
| `blocks` | string[] | O | claim ids **without** `claim:` prefix | D/L | "Discredit this and … would revive" | Pleaded points that revive if this claim is removed/discredited. Inspector builds `claim:{id}`. |
| `admissibility` | object | O | see below | L | carried for the admissibility/hearsay affordance (not yet rendered by a shipped component) | Present **only** when the underlying evidence has an admissibility problem. Omit entirely otherwise. |

`admissibility` object (when present):

| Sub-field | Type | Req | Enum | By | How to derive |
|---|---|---|---|---|---|
| `hearsay` | boolean | R | - | L | `true` if the statement is hearsay (e.g. "I am told …"). |
| `personal_knowledge` | boolean | R | - | L | `false` if not within the maker's own knowledge. |
| `note` | string | R | - | L | One-line explanation of the issue. |
| `source` | string | R | `"counsel"` · `"ai"` | - | Provenance of the judgment; `"ai"` → "AI · verify". |

### 3.6 `document` node (provenance - a tab in the bundle)

| Field | Type | Req | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `title` | string | R | - | D | inspector heading, graph label, verify dialog title | Document title, e.g. `"Change Order No 3"`. |
| `doc_type` | string | R | `contract` · `pleading` · `witness` · `expert` · `record` · `correspondence` | D | `doc_type` chip (inspector, verify dialog) | Legacy coarse type of the document. |
| `party` | string | R | `claimant` · `defendant` · `neutral` | D | `party` chip | Whose document it is. Bundle/contract docs are `neutral`. |

> Note: the `document` **node** carries only `title`/`doc_type`/`party`. The full body, dates, category
> and multi-modal fields live in the `documents` **map** (§3.9), keyed by the same tab id.

### 3.7 `edges[]`

Three kinds. Direction matters - see §5.

| Field | Type | Req | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `source` | string | R | a node `id` | D | graph, inspector, controlling evidence | Edge tail. |
| `target` | string | R | a node `id` | D | as above | Edge head. |
| `kind` | string | R | `provenance` · `coherence` · `impact` | D | graph filtering; inspector grouping | `provenance` = doc→claim; `coherence` = claim↔claim; `impact` = pleading-claim→proposition. |
| `rel` | string | R | `asserts` · `contradicts` · `supersedes` · `supports` · `caps` · `qualifies` · `attacks` · `legal_bar` · `belongs_to` | L | edge colour/label, controlling-evidence rank | The relationship. See the kind→rel mapping in §5. |
| `hard` | boolean | O | - | D/L | thicker edge; "hard" chip | `true` for decisive contradictions/supersessions that drive the solver. |
| `explanation` | string | O | - | L | inspector edge/relation body | One-line reason, e.g. "A signed variation revised the deadline …". |
| `own_goal` | boolean | O | - | L | orange "own goal" tag; feeds `stats.own_goal` | `true` when the claimant's **own** material undermines its pleaded case. |
| `verdict` | string | O | `accepted` · `rejected` | L | (carried on `impact` edges) | On `belongs_to` edges, mirrors the pleading claim's verdict. |
| `blocking` | boolean | O | - | D/L | (solver signal) | `true` if this hard edge is what rejects the pleaded point. |
| `load_bearing` | boolean | O | - | D/L | (graph/solver signal) | `true` if this support edge is the sole support of a surviving point. |

### 3.8 `clusters[]` - one per pleaded issue

The narrative + amendment layer. The inspector finds a proposition's cluster by matching `issue`
(via any of its claims) or by an `impacts` line prefixed with the proposition label.

| Field | Type | Req | By | UI | How to derive |
|---|---|---|---|---|---|
| `issue` | string | R | L | inspector cluster lookup; "Coherent story · {issue}" | Same token as the claims' `issue`. |
| `solver` | string | O | D | not rendered | e.g. `"brute_force"`. Informational. |
| `story` | string[] | R (may be `[]`) | L | inspector "Coherent story"; first line is the "Why" fallback | The coherent narrative for the issue, as ordered bullet sentences. |
| `impacts` | string[] | R (may be `[]`) | L | inspector "Why" + matching | **Each line must start with `"{propLabel}: "`** (e.g. `"P2: REJECTED_BY_COHERENT_STORY [legal overlay: SUPERSEDED] - Go-live was revised …"`). The text **after the first colon** is surfaced verbatim as the plain-language "Why". |
| `amendments` | string[] | R (may be `[]`) | L | inspector "Suggested amendments" | Lawyer-facing fixes: withdraw / qualify / reduce / address-cap / add-evidence / reframe. |

### 3.9 `documents` (map: tab id → full body) - optional overlay

Keyed by **tab id** (`"02"`, `"07"`, `"19"`…) - the same string used in `doc:` ids and anchors.
`documents["02"]` is special: it is the **Particulars of Claim** that the Pleading view renders.

| Field | Type | Req (within an entry) | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `title` | string | R | - | D | verify dialog title | Document title. |
| `doc_type` | string | R | `contract`·`pleading`·`witness`·`expert`·`record`·`correspondence` | D | `doc_type` chip in `Reader` | Same coarse type as the node. |
| `party` | string | R | `claimant`·`defendant`·`neutral` | D | `party` chip in `Reader` | Same as the node. |
| `paras` | array `[{n,text}]` | R | - | D (verbatim) | the readable body; anchor highlight target | Verbatim numbered paragraphs. `n` = 1-based paragraph number; `text` = exact paragraph text. Anchors resolve to `paras[n]`. |
| `tab` | string | O | - | D | (mirrors the map key) | The tab id, same as the key. |
| `date` | string \| null | O | ISO `yyyy-mm-dd` | D | (used by `doc_index`/chronology) | Document date. |
| `category` | string | O | `Contract`·`Amendment`·`Correspondence`·`Record`·`Internal record`·`Pleading`·`Witness (fact)`·`Witness (expert)` | D | (mirrors `doc_index` category) | Legal category (richer than `doc_type`). |
| `modality` | string | O | `document`·`email`·`video`·`photo` | D | (drives multi-modal intent; see §6) | The medium of the evidence. |
| `mime` | string | O | e.g. `text/plain`, `application/pdf`, `image/png`, `video/mp4` | D | `FileViewer` picks image/video/iframe | MIME type of `file_url`. |
| `file_url` | string \| null | O | - | D | `FileViewer` (renders the real file) | URL to the original file. When present **and** non-null, the verify dialog renders the file instead of `paras`. |
| `description` | string | O | - | D/L | (one-line description) | Short human description. |

`paras[]` entry:

| Sub-field | Type | Req | Notes |
|---|---|---|---|
| `n` | number | R | 1-based paragraph number; anchors point at this. |
| `text` | string | R | Verbatim paragraph text; every `quote` for this tab must be a literal substring of some paragraph's `text`. |

### 3.10 `doc_index[]` - the full bundle spine - optional overlay

Lists **every** tab (e.g. 01–20), including tabs with no extracted body in `documents`, so the
Chronology "Documents" table can show the whole bundle.

| Field | Type | Req | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `tab` | string | R | - | D | "Tab" column (`tabLabel`) | Tab id, e.g. `"06"`. |
| `title` | string | R | - | D | "Document" column | Title. |
| `party` | string | R | `claimant`·`defendant`·`neutral` | D | "Party" column | Whose document. |
| `date` | string \| null | O | ISO `yyyy-mm-dd` | D | "Date" column; **table sort key** | Document date. |
| `category` | string | O | same enum as `documents.category` | D | "Category" column | Legal category. |

### 3.11 `chronology[]` - the timeline of facts - optional overlay

| Field | Type | Req | Enum | By | UI | How to derive |
|---|---|---|---|---|---|---|
| `n` | number | R | - | D | row key/order | 1-based order. |
| `date` | string \| null | O | ISO `yyyy-mm-dd` | D | row date (`fmtDate`) | The fact's date; `null` shows as a placeholder dash. |
| `event` | string | R | - | L/D | the fact text | What happened, in prose. |
| `evidence` | array `[{tab,para}]` | O | - | D | one verify button per item | Supporting anchors. `tab` is a tab id; `para` is a paragraph number or `null` (whole document, no highlight). |
| `remarks` | string | O | - | L | italic counsel note | May be `""`. |
| `source` | string | O | `"counsel"` · `"ai"`/`"model"` | - | `TrustBadge` | `"counsel"` (or omit) = deterministic/human; `"ai"` → "AI · verify". |

`evidence[]` entry: `tab` (string, R), `para` (number \| null, O).

---

## 4. The LLM's job, concretely (per pleaded allegation)

For each pleaded allegation the engine must produce the following. Tags: **[D]** deterministic /
mechanical, **[L]** LLM-judged.

1. **Extract the pleaded paragraphs** **[D]** - load the Particulars of Claim into `documents["02"].paras[]` verbatim (numbered). This is the spine the Pleading view annotates.
2. **One `proposition` node per pleaded allegation** **[L]** - `text` (the allegation), `label` (`P1`, `P2`, `P9a`…). Verdict/overlay/readiness filled in step 6.
3. **One `pleading` `claim` per allegation** **[L for atomization, D for anchor]** - `polarity:"pleading"`, `anchor:"02¶n"` (the paragraph it sits at), `prop:"P_"` (its proposition), `quote` = the verbatim pleaded sentence, `source_type:"pleading"`, `weight:1.0`.
4. **Extract `bundle` claims from the evidence** **[L extraction, D anchoring]** - atomic, quote-grounded facts that bear on the allegation. Each gets `polarity:"bundle"`, an `anchor:"<tab>¶<n>"`, a **verbatim** `quote`, a `source_type`, and a `weight` from the source-strength convention (**documents > experts > witnesses > pleadings**: ~5 / ~4 / ~2 / 1). Add `legal_overlay` claims for contractual bars/caps (`source_type:"legal_clause"`). Add `absence` claims (`anchor:null`, `quote:null`) where a pleaded point has **no** supporting document.
5. **Classify the edges** **[L]**:
   - `provenance` `asserts`: each `document` → the `claim` it supports.
   - `coherence`: between claims - `contradicts` / `supersedes` (set `hard:true`), or `supports` / `caps` / `qualifies` / `attacks` / `legal_bar`. Direction = **bundle claim → pleading claim** (§5). Add `explanation`, and `own_goal:true` when the claimant's own material is what undermines its case.
   - `impact` `belongs_to`: each pleading claim → its proposition, carrying `verdict`.
6. **Per-proposition verdict + overlay + readiness** **[L]** - run the coherence/solver step: does the pleaded point survive the bundle? Set proposition `verdict`, `overlay`, `readiness`, and the targeting pleading claim's `verdict` (`accepted`/`rejected`) consistently.
7. **Source weights** **[D]** - assign `weight` deterministically from `source_type` (the convention above); set `load_bearing` / `single_source` from the support structure.
8. **One `cluster` per issue** **[L]** - `story[]` (the coherent narrative), `impacts[]` (one `"{label}: …"` line per affected proposition), `amendments[]` (lawyer-facing fixes).
9. **Chronology of facts** **[L event text, D anchors]** - dated `event`s with `evidence` anchors; mark `source:"ai"` for any fact you inferred rather than read.
10. **Admissibility flags** **[L]** - where a bundle claim rests on hearsay / out-of-knowledge evidence, attach the `admissibility` object with `source` tagging.
11. **Roll-up `stats`** **[D]** - counts (`props`/`docs`/`claims`/`rejected_pleadings`/`own_goal`) are mechanical; `readiness` and `exposure_*` are derived/judged.

---

## 5. Anchors, ids, and invariants

- **Node id prefixes**: `prop:` (proposition), `claim:` (claim), `doc:` (document). Ids are unique and stable within a case.
- **Tab == document id**: a `doc:` node's id is the tab id; `documents` is keyed by the same id; `anchor` and `chronology.evidence.tab` use the same id. `doc:07` ↔ `documents["07"]` ↔ anchor `"07¶9"` ↔ `doc_index` tab `"07"`.
- **Anchor format**: `"<tab>¶<para>"` (the separator is the pilcrow `¶`, U+00B6), e.g. `"19¶3"`. A bare `"<tab>"` (no `¶`) means the whole document (no paragraph highlight) - used in `chronology.evidence` with `para:null`.
- **Quote ⊂ paragraph (hard rule)**: `quote` must be a literal substring of `documents[tab].paras[para].text`. The highlighter uses `indexOf`; a non-verbatim quote silently loses its highlight.
- **The Particulars of Claim is tab `"02"`**: the Pleading view only annotates `documents["02"]`, and only `pleading` claims whose `anchor` starts `"02¶"` produce margin notes. If your pleading sits at a different tab, the margin-note path won't fire (the view falls back to a plain proposition list).
- **`prop` has no prefix**: a pleading claim's `prop` is the bare label (`"P2"`); the UI prepends `prop:`.
- **`blocks` ids have no prefix**: bare claim ids (`"p2_late"`); the UI prepends `claim:`.
- **Edge kind → rel** (and direction):
  - `provenance` → `asserts`, **document → claim**.
  - `coherence` → `contradicts`/`supersedes`/`supports`/`caps`/`qualifies`/`attacks`/`legal_bar`, **claim ↔ claim**.
  - `impact` → `belongs_to`, **pleading claim → proposition** (carries `verdict`).
- **Contradiction direction**: for a coherence edge that defeats a pleaded point, **`source` = the bundle (or legal_overlay) claim, `target` = the pleading claim**. The Pleading view's `controllingEvidence()` only looks at coherence edges whose **target** is the pleading claim and whose **source** is a non-pleading claim. Get this backwards and the margin note + controlling-evidence card go blank. (See `data.json`: `claim:co3_revised → claim:p2_late`, `claim:uat_signed → claim:p7_noaccept`.)
- **`issue` is the join key**: every claim and its cluster must share the exact `issue` string.

---

## 6. Multi-modal & delivery

- **Modality / mime / file_url** (on a `documents` entry) make the verify dialog render the **real** evidence rather than a transcription:
  - `modality:"document"`, `mime:"text/plain"`, `file_url:null` → the dialog renders `paras` (the default text reader).
  - `mime:"application/pdf"` + a `file_url` → rendered in an `<iframe>` (scanned/native PDFs).
  - `mime:"image/*"` + `file_url` → rendered as an `<img>` (photos, screenshots).
  - `mime:"video/*"` + `file_url` → rendered as a `<video controls>` (CCTV, screen recordings).
  - When you supply `file_url`, still supply `paras` where you can (so anchors/quotes have text to fall back to), and keep `mime` accurate - it is what selects the viewer.
- **Delivery** (either is fine, matches §(d) of INTEGRATION.md):
  - **By URL/endpoint** - a plain `GET` returns the `AppData` object (CORS-enabled). This matches a "link to the processed case".
  - **As a stored record** - the same JSON saved as the case record and read back.
- **Trust tagging** - mark every LLM-judged, human-checkable item so the UI badges "AI · verify":
  - `chronology[].source: "ai"`
  - `claim.admissibility.source: "ai"`
  - `proposition.source: "ai"` (margin-note badge)
  - Deterministic/counsel-verified items use `"counsel"` or omit `source`. When in doubt, mark `"ai"`.

---

## 7. Minimal valid example + the full worked example

### 7.1 Smallest case the frontend will render

`clusters` may be `[]`; the four overlays may be omitted. (Note: to avoid `undefined` in the
header chips, also include `own_goal`, `exposure_from`, `exposure_to`.)

```json
{
  "meta":  { "case": "Acme v Beta", "claim_no": "HT-1", "court": "TCC", "seeded": false },
  "stats": { "readiness": 0, "own_goal": 0, "props": 1, "docs": 1, "claims": 1,
             "rejected_pleadings": 0, "exposure_from": "£0", "exposure_to": "£0" },
  "nodes": [
    { "id": "prop:P1", "layer": "proposition", "label": "P1",
      "verdict": "SUPPORTED", "overlay": "NONE", "readiness": 100,
      "text": "The widget was defective." },
    { "id": "claim:c1", "layer": "claim", "label": "Defect logged",
      "fulltext": "A Sev-1 defect was recorded.", "issue": "DEFECTS",
      "polarity": "bundle", "source_type": "defect_log", "weight": 4.0,
      "verdict": "accepted", "anchor": "05¶2", "quote": "Sev-1 defect recorded.",
      "prop": null, "load_bearing": true, "single_source": false },
    { "id": "doc:05", "layer": "document", "label": "05",
      "title": "Defect Log", "doc_type": "record", "party": "neutral" }
  ],
  "edges": [
    { "source": "doc:05", "target": "claim:c1", "kind": "provenance", "rel": "asserts", "hard": false }
  ],
  "clusters": []
}
```

This renders: header chips, a one-allegation graph, and (with no `documents["02"]`) the Pleading
view's proposition-list fallback. Add `documents` + `doc_index` + `chronology` to light up verify,
the bundle spine, and the timeline.

### 7.2 The full worked example

`demo/data.json` (Meridian Retail Group plc v TechFlow Solutions Ltd) is the **complete, real**
reference: 10 propositions, 27 claims, 12 document bodies, a 20-tab `doc_index`, a 12-fact
`chronology`, 8 issue clusters and matching `sensitivity`. Every shape and enum in this spec is
confirmed against it. Copy its structure; do not contradict it.

---

### Appendix A - what the UI does **not** read (emit for parity, safe to omit)

These are in the type/`data.json` but not consumed by any shipped screen: `meta.seeded`,
`stats.props`, `stats.docs`, `stats.claims`, `stats.rejected_pleadings`, `clusters[].solver`, the
entire `sensitivity[]` array (the per-node `load_bearing` / `single_source` / `blocks` flags are what
actually render), and `claim.admissibility` (carried in the data, reserved for the admissibility
affordance, not yet wired to a visible component). Emit them for parity with `data.json` and
forward-compatibility; omitting them changes nothing on screen today.
