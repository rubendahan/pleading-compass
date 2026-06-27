# INTEGRATION.md — backend → frontend, in 2 minutes

For **Benjamin**. Goal: make your backend emit the JSON our frontend reads — or see how close you already are.
The single source of truth is the worked example **[`demo/data.json`](./data.json)** (full field reference in **[`SCHEMA.md`](./SCHEMA.md)**).

## (a) What the frontend needs

**One JSON document per case**, in our `AppData` shape. Copy the structure of `demo/data.json`.

**Required top-level keys** (the frontend won't render without these):

- `meta` — `{ case, claim_no, court, seeded }`
- `stats` — headline counters `{ readiness, own_goal, props, docs, claims, … }`
- `nodes` — the three-layer graph (see prefixes/enums below)
- `edges` — relationships between nodes
- `clusters` — one per pleaded issue (story + amendments)

**Optional keys** (frontend degrades gracefully if missing):

- `sensitivity` — load-bearing / single-source / revives-if-removed, per issue
- `documents` — map `tab → { …metadata, paras:[{n,text}] }` (full bodies)
- `doc_index` — `[{ tab, title, party, date, category }]` for every tab
- `chronology` — `[{ n, date, event, evidence:[{tab,para}], remarks, source }]`

**Node ids** are prefixed by layer: `claim:…`, `doc:…`, `prop:…`.
Each node has `layer ∈ document | claim | proposition`.

**Edges**: `{ source, target, kind, rel, hard }`.

- `kind ∈ provenance | coherence | impact`
- `rel ∈ asserts | contradicts | supersedes | supports | caps | qualifies | attacks | legal_bar | belongs_to`
  - `provenance` → `asserts` (document → claim)
  - `coherence` → `contradicts | supersedes | supports | caps | qualifies | attacks | legal_bar` (claim ↔ claim)
  - `impact` → `belongs_to` (pleading claim → proposition; carries a `verdict`)

**Anchor format**: `"<tab>¶<para>"` — e.g. `"19¶3"` (tab 19, paragraph 3). Resolves into `documents[tab].paras`.

**Enums the UI relies on:**

- proposition `verdict ∈ SUPPORTED | CONTRADICTED | NOT_ADDRESSED | UNVERIFIED`
- claim `verdict ∈ accepted | rejected`
- proposition `overlay ∈ NONE | CONTRACTUALLY_BARRED | SUPERSEDED | CAPPED | CAUSATION_PROBLEM | BURDEN_PROBLEM`

## (b) Mapping from your model to ours

| Benjamin (Architecture.md) | Ours |
|---|---|
| claim (from pleading) | node layer `proposition` (+ a pleading-side `claim`) |
| evidence node | node layer `document` (+ a bundle `claim`) |
| evidence `time` | document `date` / a `chronology` fact |
| evidence `type` (email/witness/video) | document `category` / `modality`+`mime` |
| evidence NL `description` | document `description` |
| claim→evidence (used-by) | edge `rel:"asserts"` (provenance) / impact edge |
| evidence↔evidence support/contradiction | coherence edge `rel:"supports"`/`"contradicts"` |
| claim robustness | proposition `verdict` + `readiness` |
| top-K similarity (extrapolation risk) | verdict `NOT_ADDRESSED` / `UNVERIFIED` |
| pleading improvements | `clusters[].amendments` |

Note the one twist: our reasoning node is the **claim**, not the document. A document `asserts` a bundle
`claim`; a pleading `claim` `belongs_to` a `proposition`. If you only have your two layers, emit
`document` + `proposition` nodes and `asserts`/`belongs_to` edges — we can still draw the graph.

## (c) The golden rule

> **Emit what you can; OMIT any score/edge/link you don't have.** The frontend degrades gracefully —
> a missing `sensitivity`, `chronology`, `quote`, or `readiness` just hides that affordance. **Don't block on completeness.**

## (d) Delivery

Either works:

- **By URL / endpoint** — the frontend loads a case from a URL returning this JSON (matches your
  "link to the processed case" delivery). Plain `GET` → the `AppData` object, CORS-enabled.
- **As a stored record** — the same JSON saved as the case record and read back by the frontend.

## (e) Trust note (mark anything LLM-judged)

Anything an LLM judged should be **marked**, so the UI can badge it **"AI · verify"**:

- chronology fact → `"source": "ai"`
- claim admissibility → `admissibility.source: "ai"`

Deterministic / human-authored items use `"source": "counsel"` (or omit `source`). When in doubt, mark it `ai`.

## (f) Smallest valid shape

```json
{
  "meta":  { "case": "Acme v Beta", "claim_no": "HT-1", "court": "TCC", "seeded": false },
  "stats": { "readiness": 0, "props": 1, "docs": 1, "claims": 1 },
  "nodes": [
    { "id": "prop:P1", "layer": "proposition", "label": "P1", "verdict": "SUPPORTED", "overlay": "NONE", "readiness": 100, "text": "The widget was defective." },
    { "id": "claim:c1", "layer": "claim", "label": "Defect logged", "verdict": "accepted", "prop": "P1", "anchor": "05¶2", "quote": "Sev-1 defect recorded." },
    { "id": "doc:05", "layer": "document", "label": "05", "title": "Defect Log", "party": "neutral" }
  ],
  "edges": [
    { "source": "doc:05", "target": "claim:c1", "kind": "provenance", "rel": "asserts", "hard": false }
  ],
  "clusters": []
}
```

## (optional) `toAppData(hisJson)` adapter sketch

If you can't emit our shape directly, map your field names like this (pseudo-JS):

```js
function toAppData(his) {
  const nodes = [], edges = [];

  // your pleading claims → propositions
  his.claims.forEach((c, i) => {
    const pid = `prop:P${i + 1}`;
    nodes.push({ id: pid, layer: "proposition", label: `P${i + 1}`,
                 text: c.text, readiness: c.robustness ?? null,
                 verdict: c.robustness >= 50 ? "SUPPORTED" : "UNVERIFIED", overlay: "NONE" });
  });

  // your evidence nodes → documents
  his.evidence.forEach(e => {
    nodes.push({ id: `doc:${e.id}`, layer: "document", label: e.id, title: e.title,
                 date: e.time, category: mapType(e.type), modality: mapModality(e.type),
                 description: e.description, party: "neutral" });
  });

  // claim→evidence (used-by, cosine sim) → asserts (provenance)
  his.usedBy.forEach(u =>
    edges.push({ source: `doc:${u.evidenceId}`, target: `prop:P${u.claimIdx + 1}`,
                 kind: "impact", rel: "belongs_to", hard: false, score: u.cosine }));

  // evidence↔evidence support/contradiction → coherence
  his.relations.forEach(r =>
    edges.push({ source: `doc:${r.a}`, target: `doc:${r.b}`, kind: "coherence",
                 rel: r.polarity === "contradiction" ? "contradicts" : "supports",
                 hard: r.polarity === "contradiction" }));

  return { meta: his.meta, stats: his.stats, nodes, edges,
           clusters: his.suggestions ?? [] };   // pleading improvements → clusters[].amendments
}
// mapType: email→"Correspondence", witness→"Witness (fact)", video→"Record", …
// mapModality: email→"email", video→"video", photo→"photo", else "document"
```

OMIT any field above you don't have — see the golden rule.
