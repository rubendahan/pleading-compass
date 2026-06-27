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
