// Shared types and helpers for the Pleading-to-Proof console.

export type Verdict =
  | "SUPPORTED"
  | "CONTRADICTED"
  | "NOT_ADDRESSED"
  | "UNVERIFIED"
  | "accepted"
  | "rejected";

export type Layer = "document" | "claim" | "proposition";

export interface PropositionNode {
  id: string;
  layer: "proposition";
  label: string;
  verdict: "SUPPORTED" | "CONTRADICTED" | "NOT_ADDRESSED" | "UNVERIFIED";
  overlay: string;
  readiness: number;
  text: string;
  /** True when support is empty/flagged: the UI shows an "AI · verify" call-to-action
   *  instead of leaving a silent blank (the "paragraph with nothing there" fix). */
  verify?: boolean;
  verify_reason?: string;
}

export interface ClaimNode {
  id: string;
  layer: "claim";
  label: string;
  fulltext: string;
  issue: string;
  polarity: "pleading" | "bundle" | "legal_overlay";
  source_type: string;
  weight: number;
  verdict: "accepted" | "rejected";
  anchor: string | null;
  quote: string | null;
  prop: string | null;
  load_bearing: boolean;
  single_source: boolean;
  blocks?: string[];
  /** True when this claim has no quote-grounded support: surface "AI · verify". */
  verify?: boolean;
  verify_reason?: string;
}

export interface DocumentNode {
  id: string;
  layer: "document";
  label: string;
  title: string;
  doc_type: string;
  party: string;
}

export type DataNode = PropositionNode | ClaimNode | DocumentNode;

export type EdgeRel =
  | "asserts"
  | "contradicts"
  | "supersedes"
  | "supports"
  | "caps"
  | "qualifies"
  | "attacks"
  | "legal_bar"
  | "belongs_to";

export interface DataEdge {
  source: string;
  target: string;
  kind: "provenance" | "coherence" | "impact";
  rel: EdgeRel;
  hard?: boolean;
  explanation?: string;
  own_goal?: boolean;
  verdict?: string;
  blocking?: boolean;
  load_bearing?: boolean;
}

export interface Cluster {
  issue: string;
  solver?: string;
  story: string[];
  impacts: string[];
  amendments: string[];
}

export interface AppData {
  meta: { case: string; claim_no: string; court: string; seeded?: boolean };
  stats: {
    readiness: number;
    own_goal: number;
    props: number;
    docs: number;
    claims: number;
    rejected_pleadings: number;
    exposure_from: string;
    exposure_to: string;
  };
  nodes: DataNode[];
  edges: DataEdge[];
  clusters: Cluster[];
  sensitivity: Array<{
    issue: string;
    load_bearing: Record<string, string[]>;
    single_source: string[];
    revives_if_removed: Record<string, string[]>;
  }>;
  /** Full paragraph text per cited document, for in-context source verification. */
  documents?: Record<string, {
    title: string; doc_type: string; party: string;
    tab?: string; date?: string | null; category?: string;
    modality?: string; mime?: string; file_url?: string | null; description?: string;
    paras: Array<{ n: number; text: string }>;
  }>;
  /** All tabs with date + legal category — the chronology of documents. */
  doc_index?: Array<{ tab: string; title: string; party: string; date?: string | null; category?: string }>;
  /** Chronology of facts, each anchored for one-click verify. */
  chronology?: Array<{
    n: number; date?: string | null; event: string;
    evidence?: Array<{ tab: string; para?: number | null }>;
    remarks?: string; source?: string;
  }>;
}

export type Mode = "stress" | "coherence";

// Colours (tokens mirrored from styles.css).
export const COLORS = {
  bg: "#f5f3ee",
  panel: "#fbfaf6",
  panel2: "#efece4",
  hair: "#d8d3c7",
  ink: "#14110d",
  inkDim: "#6b6760",
  accepted: "#2f7a55",
  rejected: "#a83a2b",
  legal: "#a87422",
  absence: "#8a857a",
  accent: "#14110d",
  brass: "#8b6f3c",
  orange: "#b0561f",
} as const;

export function verdictColor(v: string | undefined | null): string {
  if (!v) return COLORS.absence;
  const k = v.toUpperCase();
  if (k === "SUPPORTED" || k === "ACCEPTED") return COLORS.accepted;
  if (k === "CONTRADICTED" || k === "REJECTED") return COLORS.rejected;
  if (k === "NOT_ADDRESSED") return COLORS.absence;
  if (k === "UNVERIFIED") return COLORS.legal;
  return COLORS.absence;
}

export function nodeColor(n: DataNode): string {
  if (n.layer === "proposition") return verdictColor(n.verdict);
  if (n.layer === "claim") {
    if (n.polarity === "legal_overlay") return COLORS.legal;
    return verdictColor(n.verdict);
  }
  return COLORS.accent;
}

export function edgeColor(rel: EdgeRel): string {
  switch (rel) {
    case "contradicts":
      return COLORS.rejected;
    case "supersedes":
    case "attacks":
      return COLORS.orange;
    case "supports":
      return COLORS.accepted;
    case "caps":
    case "qualifies":
    case "legal_bar":
      return COLORS.legal;
    case "belongs_to":
      return COLORS.accent;
    case "asserts":
    default:
      return COLORS.accent;
  }
}

export function relLabel(rel: EdgeRel): string {
  return rel.replace("_", " ").toUpperCase();
}

export function srcId(s: string | { id: string }): string {
  return typeof s === "string" ? s : s.id;
}

/** A bundle document id is its litigation Tab number. "04" -> "Tab 4". */
export function tabLabel(docId: string | null | undefined): string {
  if (!docId) return "";
  const n = parseInt(docId, 10);
  return Number.isNaN(n) ? `Tab ${docId}` : `Tab ${n}`;
}

/** Format a source anchor "04¶9" as "Tab 4 · ¶9" for lawyer-facing references. */
export function anchorLabel(anchor: string | null | undefined): string {
  if (!anchor) return "";
  const [doc, para] = anchor.split("¶");
  return para ? `${tabLabel(doc)} · ¶${para}` : tabLabel(doc);
}

/** A pointer into a source document: which paragraph to open, and the verbatim
 *  quote to highlight there. `anchor === null` means "no grounded source" — the
 *  reader then shows a verify call-to-action rather than a silent blank. */
export interface SourceRef {
  anchor: string | null;
  quote: string | null;
  /** The node the ref was resolved from, so the reader can offer "open full analysis". */
  nodeId: string;
}

/** Resolve any graph node to the source it should open in the reader.
 *  - claim node      → its own anchor + verbatim quote
 *  - document node   → the bare tab id (whole document, no highlight)
 *  - proposition     → its controlling evidence (the heaviest non-pleading coherence
 *                      claim into the proposition's pleading claim); failing that,
 *                      the pleading claim's own "02¶n" anchor. */
export function resolveNodeSource(nodeId: string, data: AppData): SourceRef {
  const node = data.nodes.find((n) => n.id === nodeId);
  if (!node) return { anchor: null, quote: null, nodeId };

  if (node.layer === "document") {
    return { anchor: node.label, quote: null, nodeId };
  }
  if (node.layer === "claim") {
    return { anchor: node.anchor, quote: node.quote, nodeId };
  }

  // Proposition: follow coherence edges into its pleading claim(s).
  const propKey = node.id.replace("prop:", "");
  const pleadingClaims = data.nodes.filter(
    (n): n is ClaimNode =>
      n.layer === "claim" && n.prop === propKey && n.polarity === "pleading",
  );
  const pleadingIds = new Set(pleadingClaims.map((n) => n.id));

  let best: { c: ClaimNode; rank: number } | null = null;
  if (pleadingIds.size > 0) {
    for (const e of data.edges) {
      if (e.kind !== "coherence" || !pleadingIds.has(srcId(e.target))) continue;
      const src = data.nodes.find((n) => n.id === srcId(e.source));
      if (!src || src.layer !== "claim" || (src as ClaimNode).polarity === "pleading") continue;
      const sc = src as ClaimNode;
      const relRank =
        e.rel === "contradicts" || e.rel === "supersedes"
          ? 4
          : e.rel === "legal_bar" || e.rel === "caps"
            ? 3
            : e.rel === "supports"
              ? 3
              : 1;
      const rank = relRank * 100 + (sc.weight ?? 0);
      if (!best || rank > best.rank) best = { c: sc, rank };
    }
  }
  if (best) return { anchor: best.c.anchor, quote: best.c.quote, nodeId };

  // No controlling evidence: fall back to the pleading claim's own paragraph.
  const pleading = pleadingClaims[0];
  if (pleading) return { anchor: pleading.anchor, quote: pleading.quote, nodeId };
  return { anchor: null, quote: null, nodeId };
}
