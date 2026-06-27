# Evidence Coherence Console — visual demo

A self-contained, dependency-free HTML demo of Pleading-to-Proof rendered as a
**three-layer, claim-centric graph**:

```
Document (provenance)  ──asserts──▶  Claim (reasoning)  ──belongs_to──▶  Proposition (target)
                                      Claim  ◀─contradicts / supersedes / caps─▶  Claim
```

The reasoning nodes are **quote-grounded atomic claims**, never raw documents — documents
and paragraphs are provenance only. Two paradigms share the graph:

- **Pleading Stress Test** — each pleaded proposition traced to its evidence for and against.
- **Bundle Coherence** — a deterministic max-weight solver keeps the strongest set of
  non-contradictory claims; rejected pleadings sink away, the surviving coherent story stays lit.

Click any node to inspect its verbatim quote, source anchor, weight and conflicts.
Slogan: **LLM local, solver global.**

## Open it

Just open `index.html` in any browser — no server, no build step, works offline. The
force-directed graph is hand-written SVG (no CDN); fonts load from Google Fonts when online
and fall back to system faces offline.

Deep links: `index.html?mode=coherence` opens the bundle-first view;
`index.html?inspect=claim:uat_signed` opens with a node already selected.

## Rebuild the data

`index.html` embeds the **real** Meridian analysis, exported from the engine. To regenerate
after changing the analysis:

```bash
python demo/build.py        # reads index.template.html, writes index.html
```

`build.py` runs `coherence.analyse` + the pleading-first pipeline over the bundle and injects
the graph as JSON. Quotes are loaded verbatim when the DOCX bundle is on disk (checked via
`judges.base.verbatim_ok`); otherwise claims show their anchor only. This is a **seeded
vertical POC** over the synthetic bundle — paragraph-level LLM extraction is the future drop-in.

Files: `build.py` (exporter), `index.template.html` (frontend source), `index.html` (generated).
