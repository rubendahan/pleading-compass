import { useEffect, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import type { AppData, ClaimNode, DataEdge, DataNode, PropositionNode } from "@/lib/pleading";
import { COLORS, anchorLabel, edgeColor, relLabel, srcId, verdictColor } from "@/lib/pleading";
import { summariseNode } from "@/lib/summary.functions";
import { AnchorButton } from "./SourceReader";

interface Props {
  data: AppData;
  caseId?: string;
  selectedId: string | null;
  selectedEdge: DataEdge | null;
  onSelect: (id: string | null) => void;
  onClose: () => void;
}

export default function Inspector({ data, caseId, selectedId, selectedEdge, onSelect, onClose }: Props) {
  const node = selectedId ? data.nodes.find((n) => n.id === selectedId) ?? null : null;


  return (
    <aside
      className="flex h-full flex-col overflow-hidden rounded-lg border"
      style={{ borderColor: COLORS.hair, background: COLORS.panel }}
    >
      <header
        className="flex items-center justify-between border-b px-4 py-3"
        style={{ borderColor: COLORS.hair }}
      >
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-dim">
            Inspector
          </div>
          <h2 className="font-display text-base text-ink">
            {selectedEdge
              ? "Relation"
              : node
                ? node.layer === "proposition"
                  ? `Pleaded allegation ${node.label}`
                  : node.layer === "claim"
                    ? "Claim"
                    : `Document ${node.label}`
                : "Nothing selected"}
          </h2>
        </div>
        {(node || selectedEdge) && (
          <button
            onClick={onClose}
            className="rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-ink-dim hover:text-ink"
            style={{ borderColor: COLORS.hair }}
          >
            Close
          </button>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {!node && !selectedEdge && <EmptyState />}
        {node?.layer === "proposition" && (
          <PropositionView data={data} node={node} onSelect={onSelect} />
        )}
        {node?.layer === "claim" && (
          <ClaimView data={data} node={node} onSelect={onSelect} />
        )}
        {node?.layer === "document" && (
          <DocumentView data={data} node={node} onSelect={onSelect} />
        )}
        {selectedEdge && <EdgeView data={data} edge={selectedEdge} onSelect={onSelect} />}
        {node && caseId && <AiSummary caseId={caseId} nodeId={node.id} />}
      </div>
    </aside>
  );
}

function AiSummary({ caseId, nodeId }: { caseId: string; nodeId: string }) {
  const call = useServerFn(summariseNode);
  const [state, setState] = useState<{ loading: boolean; text: string | null; err: string | null }>({
    loading: false,
    text: null,
    err: null,
  });

  // Reset when the selected node changes.
  useEffect(() => { setState({ loading: false, text: null, err: null }); }, [nodeId]);

  const run = async () => {
    setState({ loading: true, text: null, err: null });
    try {
      const { summary } = await call({ data: { caseId, nodeId } });
      setState({ loading: false, text: summary, err: null });
    } catch (e: any) {
      setState({ loading: false, text: null, err: String(e?.message ?? e) });
    }
  };

  return (
    <div className="rounded-md border p-3" style={{ borderColor: COLORS.hair, background: COLORS.panel2 }}>
      <div className="mb-2 flex items-center justify-between">
        <SectionHeading>Note</SectionHeading>
        <button
          onClick={run}
          disabled={state.loading}
          className="rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-widest transition hover:bg-bg/40 disabled:opacity-50"
          style={{ borderColor: COLORS.hair, color: COLORS.ink }}
        >
          {state.loading ? "writing" : state.text ? "regenerate" : "generate"}
        </button>
      </div>
      {state.text && (
        <p className="text-[13px] leading-relaxed text-ink whitespace-pre-wrap">{state.text}</p>
      )}
      {state.err && (
        <p className="text-[12px] leading-snug" style={{ color: COLORS.rejected }}>{state.err}</p>
      )}
      {!state.text && !state.err && !state.loading && (
        <p className="text-[11px] italic text-ink-dim">
          A short note on this node and its links.
        </p>
      )}
    </div>
  );
}



function EmptyState() {
  return (
    <div className="text-sm leading-relaxed text-ink-dim">
      <p>
        Select a pleaded allegation in the centre column, or click any node or edge in the
        graph.
      </p>
      <ul className="mt-4 space-y-2 font-mono text-[11px] uppercase tracking-widest">
        <li>· allegation: why it holds or falls</li>
        <li>· claim: the exact quote and where it comes from</li>
        <li>· link: the relation and the reason</li>
      </ul>
    </div>
  );
}

function VerdictPill({ verdict }: { verdict: string }) {
  const c = verdictColor(verdict);
  return (
    <span
      className="verdict-pill"
      style={{ borderColor: c, color: c, background: `${c}1A` }}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: c }} />
      {verdict.replace("_", " ")}
    </span>
  );
}

function OverlayChip({ overlay }: { overlay: string }) {
  if (!overlay || overlay === "NONE") return null;
  return (
    <span
      className="verdict-pill"
      style={{ borderColor: COLORS.legal, color: COLORS.legal, background: `${COLORS.legal}1A` }}
    >
      legal overlay · {overlay.replace(/_/g, " ").toLowerCase()}
    </span>
  );
}

function ReadinessBar({ value }: { value: number }) {
  const c = value >= 70 ? COLORS.accepted : value >= 30 ? COLORS.legal : COLORS.rejected;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-widest text-ink-dim">
        <span>Readiness</span>
        <span style={{ color: c }}>{value}/100</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: COLORS.hair }}>
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${value}%`, background: c }}
        />
      </div>
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-ink-dim">
      {children}
    </h3>
  );
}

/** A small brass flag used for load-bearing / single-source warnings. */
function FlagPill({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="verdict-pill"
      style={{ borderColor: COLORS.brass, color: COLORS.brass, background: `${COLORS.brass}1A` }}
    >
      {children}
    </span>
  );
}

/** A demoted, clearly-labelled section. Collapsed by default so the verify path
 *  stays front and centre; expand for the supporting analysis. */
function Collapsible({
  title,
  count,
  defaultOpen = false,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <details
      open={defaultOpen}
      className="group rounded-md border"
      style={{ borderColor: COLORS.hair, background: COLORS.panel2 }}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-ink-dim [&::-webkit-details-marker]:hidden">
        <span>
          {title}
          {count != null ? ` · ${count}` : ""}
        </span>
        <span aria-hidden className="transition-transform duration-150 group-open:rotate-90">
          ›
        </span>
      </summary>
      <div className="space-y-4 px-3 pb-3 pt-1">{children}</div>
    </details>
  );
}

function PropositionView({
  data,
  node,
  onSelect,
}: {
  data: AppData;
  node: PropositionNode;
  onSelect: (id: string) => void;
}) {
  const propKey = node.id.replace("prop:", "");
  const claims = data.nodes.filter(
    (n): n is ClaimNode => n.layer === "claim" && n.prop === propKey,
  );
  // Cluster: find issue from any associated claim.
  const sampleClaim = data.nodes.find(
    (n): n is ClaimNode => n.layer === "claim" && n.prop === propKey,
  );
  let cluster = sampleClaim
    ? data.clusters.find((c) => c.issue === sampleClaim.issue)
    : null;
  // Fallback: also check impacts strings for the proposition label.
  if (!cluster) {
    cluster = data.clusters.find((c) =>
      c.impacts.some((i) => i.startsWith(`${node.label}:`)),
    );
  }
  const impact = cluster?.impacts.find((i) => i.startsWith(`${node.label}:`));
  // The single most decisive claim: the bundle/legal evidence that drives the verdict
  // (follow the contradiction/support edges), falling back to whatever claim we have.
  const controlling = controllingFromEdges(propKey, data) ?? pickControlling(claims);
  // A short, plain "why" for the verdict. The impact line carries it; otherwise
  // fall back to the opening line of the coherent story. (No duplicate restatement.)
  const why = impact
    ? impact.slice(impact.indexOf(":") + 1).trim()
    : cluster?.story[0] ?? null;
  const hasAnalysis = Boolean(
    cluster?.story.length || cluster?.amendments.length || claims.length,
  );

  return (
    <div className="space-y-4">
      {/* What this is + the verdict. */}
      <div className="flex flex-wrap items-center gap-2">
        <VerdictPill verdict={node.verdict} />
        <OverlayChip overlay={node.overlay} />
      </div>
      <p className="text-[15px] leading-relaxed text-ink">{node.text}</p>
      <ReadinessBar value={node.readiness} />

      {/* The controlling evidence, with a one-click verify path. */}
      {controlling ? (
        <ControllingEvidence claim={controlling} documents={data.documents} onSelect={onSelect} />
      ) : (
        <div className="rounded border p-3 text-[12px] italic text-ink-dim" style={{ borderColor: COLORS.hair }}>
          No claims are pleaded to this allegation yet.
        </div>
      )}

      {/* A short, plain-language why. */}
      {why && (
        <div>
          <SectionHeading>Why</SectionHeading>
          <p className="text-[13px] leading-relaxed text-ink">{why}</p>
        </div>
      )}

      {/* Everything supporting, tucked away and clearly labelled. */}
      {hasAnalysis && (
        <Collapsible title="Analysis">
          {cluster && cluster.story.length > 0 && (
            <div>
              <SectionHeading>Coherent story · {cluster.issue.toLowerCase()}</SectionHeading>
              <ul className="space-y-1.5 text-[13px] leading-relaxed text-ink-dim">
                {cluster.story.map((s, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="mt-1 inline-block h-1 w-1 shrink-0 rounded-full" style={{ background: COLORS.accent }} />
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {claims.length > 0 && (
            <div>
              <SectionHeading>Claims targeting this allegation · {claims.length}</SectionHeading>
              <ul className="space-y-2">
                {claims.map((c) => (
                  <ClaimRow key={c.id} claim={c} onSelect={onSelect} />
                ))}
              </ul>
            </div>
          )}

          {cluster && cluster.amendments.length > 0 && (
            <div>
              <SectionHeading>Suggested amendments</SectionHeading>
              <ul className="space-y-2 text-[13px] leading-relaxed text-ink">
                {cluster.amendments.map((a, i) => (
                  <li key={i} className="rounded border-l-2 pl-3" style={{ borderColor: COLORS.legal }}>
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-[11px] italic text-ink-dim">Coherence signal, not a verdict.</p>
        </Collapsible>
      )}
    </div>
  );
}

/** The bundle/legal claim that actually drives a proposition's verdict: follow the
 *  coherence edges into its pleading claim and pick the heaviest contradicting /
 *  superseding / barring / supporting evidence (never the pleading restating itself). */
function controllingFromEdges(propKey: string, data: AppData): ClaimNode | null {
  const pleadingIds = new Set(
    data.nodes
      .filter((n): n is ClaimNode => n.layer === "claim" && n.prop === propKey && n.polarity === "pleading")
      .map((n) => n.id),
  );
  if (pleadingIds.size === 0) return null;
  let best: { c: ClaimNode; rank: number } | null = null;
  for (const e of data.edges) {
    if (e.kind !== "coherence" || !pleadingIds.has(srcId(e.target))) continue;
    const src = data.nodes.find((n) => n.id === srcId(e.source));
    if (!src || src.layer !== "claim" || (src as ClaimNode).polarity === "pleading") continue;
    const sc = src as ClaimNode;
    const relRank =
      e.rel === "contradicts" || e.rel === "supersedes" ? 4
        : e.rel === "legal_bar" || e.rel === "caps" ? 3
          : e.rel === "supports" ? 3 : 1;
    const rank = relRank * 100 + (sc.weight ?? 0);
    if (!best || rank > best.rank) best = { c: sc, rank };
  }
  return best?.c ?? null;
}

/** Pick the most decisive claim for an allegation: verifiable first (quote +
 *  anchor), then load-bearing, then heaviest weight. */
function pickControlling(claims: ClaimNode[]): ClaimNode | null {
  if (claims.length === 0) return null;
  const verifiable = claims.filter((c) => c.quote && c.anchor);
  const pool = verifiable.length > 0 ? verifiable : claims;
  return [...pool].sort((a, b) => {
    if (a.load_bearing !== b.load_bearing) return a.load_bearing ? -1 : 1;
    return (b.weight ?? 0) - (a.weight ?? 0);
  })[0];
}

/** The lead evidence card on an allegation: the claim, its verdict, and a clear
 *  verify button straight to the source paragraph. */
function ControllingEvidence({
  claim,
  documents,
  onSelect,
}: {
  claim: ClaimNode;
  documents: AppData["documents"];
  onSelect: (id: string) => void;
}) {
  const c = verdictColor(claim.verdict);
  return (
    <div
      className="rounded-md border p-3"
      style={{ borderColor: COLORS.hair, borderLeftWidth: 3, borderLeftColor: c, background: COLORS.bg }}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <SectionHeading>Controlling evidence</SectionHeading>
        <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: c }}>
          {claim.verdict}
        </span>
      </div>
      <p className="text-[13px] leading-snug text-ink">{claim.fulltext}</p>
      {claim.quote && (
        <blockquote
          className="mt-2 border-l-2 pl-3 font-mono text-[12px] leading-relaxed text-ink-dim"
          style={{ borderColor: c }}
        >
          “{claim.quote}”
        </blockquote>
      )}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <button
          onClick={() => onSelect(claim.id)}
          className="font-mono text-[10px] uppercase tracking-widest text-ink-dim underline-offset-2 hover:text-ink hover:underline"
        >
          open claim
        </button>
        {claim.anchor && (
          <AnchorButton
            anchor={claim.anchor}
            quote={claim.quote}
            documents={documents}
            label={anchorLabel(claim.anchor)}
          />
        )}
      </div>
    </div>
  );
}

function ClaimRow({
  claim,
  onSelect,
}: {
  claim: ClaimNode;
  onSelect: (id: string) => void;
}) {
  const c = verdictColor(claim.verdict);
  return (
    <li>
      <button
        onClick={() => onSelect(claim.id)}
        className="group block w-full rounded border p-2 text-left transition hover:bg-bg/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        style={{ borderColor: COLORS.hair, borderLeftWidth: 3, borderLeftColor: c }}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">
            {claim.polarity} · {claim.source_type.replace(/_/g, " ")}
          </span>
          <span className="font-mono text-[10px]" style={{ color: c }}>
            {claim.verdict}
          </span>
        </div>
        <p className="mt-1 text-[13px] leading-snug text-ink">{claim.fulltext}</p>
        {claim.anchor && (
          <div className="mt-1 font-mono text-[10px] text-ink-dim">{anchorLabel(claim.anchor)}</div>
        )}
      </button>
    </li>
  );
}

function ClaimView({
  data,
  node,
  onSelect,
}: {
  data: AppData;
  node: ClaimNode;
  onSelect: (id: string) => void;
}) {
  const c = verdictColor(node.verdict);
  const relations = data.edges.filter(
    (e) => (e.source === node.id || e.target === node.id) && e.kind === "coherence",
  );
  const provenance = data.edges.filter(
    (e) => e.kind === "provenance" && e.target === node.id,
  );
  const hasAnalysis = Boolean(
    node.load_bearing ||
      node.single_source ||
      (node.blocks && node.blocks.length > 0) ||
      provenance.length > 0 ||
      relations.length > 0,
  );

  return (
    <div className="space-y-4">
      {/* What this is + the verdict, with only the warning flags kept loud. */}
      <div className="flex flex-wrap items-center gap-2">
        <VerdictPill verdict={node.verdict} />
        {node.load_bearing && <FlagPill>load-bearing</FlagPill>}
        {node.single_source && <FlagPill>single source</FlagPill>}
      </div>
      <div className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">
        {node.polarity} · {node.source_type.replace(/_/g, " ")} · weight {node.weight.toFixed(1)}
      </div>

      {/* The pleaded claim. */}
      <p className="text-[15px] leading-relaxed text-ink">{node.fulltext}</p>

      {/* The verbatim quote and the one-click verify path: the heart of the job. */}
      {node.quote ? (
        <div className="rounded-md border p-3" style={{ borderColor: COLORS.hair, background: COLORS.bg }}>
          <div className="mb-2 flex items-center justify-between gap-2">
            <SectionHeading>Verbatim quote</SectionHeading>
            <span
              className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest"
              style={{ color: COLORS.accepted, background: `${COLORS.accepted}14` }}
            >
              ✓ verbatim
            </span>
          </div>
          <blockquote
            className="border-l-2 pl-3 font-mono text-[12px] leading-relaxed text-ink"
            style={{ borderColor: c }}
          >
            “{node.quote}”
          </blockquote>
          {node.anchor && (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">
                Verify against source
              </span>
              <AnchorButton
                anchor={node.anchor}
                quote={node.quote}
                documents={data.documents}
                label={anchorLabel(node.anchor)}
              />
            </div>
          )}
        </div>
      ) : (
        <div className="rounded border p-3 text-[12px] italic text-ink-dim" style={{ borderColor: COLORS.hair }}>
          No quote-grounded support found in this bundle.
        </div>
      )}

      {/* Supporting analysis, demoted and out of the way until needed. */}
      {hasAnalysis && (
        <Collapsible title="Analysis">
          {(node.load_bearing || node.single_source) && (
            <div
              className="rounded-md border-l-2 pl-3 text-[12px] leading-relaxed text-ink"
              style={{ borderColor: COLORS.brass, background: `${COLORS.brass}0D` }}
            >
              <span className="font-mono uppercase tracking-widest" style={{ color: COLORS.brass }}>
                Load-bearing.{" "}
              </span>
              This point rests on a single source. Discredit it and it falls.
            </div>
          )}

          {node.blocks && node.blocks.length > 0 && (
            <div className="rounded border p-3 text-[12px] leading-relaxed text-ink-dim" style={{ borderColor: COLORS.hair }}>
              <SectionHeading>If discredited</SectionHeading>
              Discredit this and{" "}
              {node.blocks.map((b, i) => (
                <span key={b}>
                  <button
                    className="font-mono text-[11px] underline-offset-2 hover:underline"
                    style={{ color: COLORS.accent }}
                    onClick={() => onSelect(`claim:${b}`)}
                  >
                    {b}
                  </button>
                  {i < node.blocks!.length - 1 ? ", " : ""}
                </span>
              ))}{" "}
              would revive.
            </div>
          )}

          {provenance.length > 0 && (
            <div>
              <SectionHeading>Source</SectionHeading>
              <ul className="space-y-1">
                {provenance.map((e) => {
                  const doc = data.nodes.find((n) => n.id === e.source);
                  if (!doc) return null;
                  return (
                    <li key={e.source}>
                      <button
                        onClick={() => onSelect(e.source)}
                        className="flex w-full items-center justify-between rounded border px-2 py-1.5 text-left text-[12px] hover:bg-bg/40"
                        style={{ borderColor: COLORS.hair }}
                      >
                        <span className="text-ink">{(doc as any).title}</span>
                        <span className="font-mono text-[10px] text-ink-dim">{doc.label}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {relations.length > 0 && (
            <div>
              <SectionHeading>Coherence relations</SectionHeading>
              <ul className="space-y-2">
                {relations.map((e, i) => (
                  <RelationRow key={i} edge={e} self={node.id} data={data} onSelect={onSelect} />
                ))}
              </ul>
            </div>
          )}
        </Collapsible>
      )}
    </div>
  );
}

function RelationRow({
  edge,
  self,
  data,
  onSelect,
}: {
  edge: DataEdge;
  self: string;
  data: AppData;
  onSelect: (id: string) => void;
}) {
  const otherId = edge.source === self ? edge.target : edge.source;
  const other = data.nodes.find((n) => n.id === otherId);
  const direction = edge.source === self ? "→" : "←";
  const c = edgeColor(edge.rel);
  const otherLabel =
    other?.layer === "proposition"
      ? (other as PropositionNode).label
      : other?.layer === "claim"
        ? (other as ClaimNode).fulltext
        : other
          ? `Doc ${(other as any).label} · ${(other as any).title}`
          : otherId;

  return (
    <li>
      <button
        onClick={() => onSelect(otherId)}
        className="block w-full rounded border p-2 text-left hover:bg-bg/40"
        style={{ borderColor: COLORS.hair, borderLeftWidth: 3, borderLeftColor: c }}
      >
        <div className="font-mono text-[10px] uppercase tracking-widest" style={{ color: c }}>
          {relLabel(edge.rel)} {direction}{" "}
          {other?.layer === "proposition" ? (other as PropositionNode).label : ""}
          {edge.own_goal && (
            <span className="ml-2" style={{ color: COLORS.orange }}>· own goal</span>
          )}
        </div>
        <p className="mt-1 text-[12px] leading-snug text-ink">{otherLabel}</p>
        {edge.explanation && (
          <p className="mt-1 text-[12px] leading-snug text-ink-dim">{edge.explanation}</p>
        )}
      </button>
    </li>
  );
}

function DocumentView({
  data,
  node,
  onSelect,
}: {
  data: AppData;
  node: DataNode & { layer: "document"; title: string; doc_type: string; party: string };
  onSelect: (id: string) => void;
}) {
  const claims = data.edges
    .filter((e) => e.kind === "provenance" && e.source === node.id)
    .map((e) => data.nodes.find((n) => n.id === e.target))
    .filter((n): n is ClaimNode => !!n && n.layer === "claim");

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="chip">{node.doc_type}</span>
        <span className="chip">{node.party}</span>
        <span className="chip font-mono">doc {node.label}</span>
      </div>
      <h3 className="font-display text-lg text-ink">{node.title}</h3>

      <div>
        <SectionHeading>Claims asserted</SectionHeading>
        <ul className="space-y-2">
          {claims.map((c) => (
            <ClaimRow key={c.id} claim={c} onSelect={onSelect} />
          ))}
        </ul>
      </div>
    </div>
  );
}

function EdgeView({
  data,
  edge,
  onSelect,
}: {
  data: AppData;
  edge: DataEdge;
  onSelect: (id: string) => void;
}) {
  const c = edgeColor(edge.rel);
  const src = data.nodes.find((n) => n.id === edge.source);
  const tgt = data.nodes.find((n) => n.id === edge.target);
  const fmt = (n: DataNode | undefined) => {
    if (!n) return "?";
    if (n.layer === "proposition") return n.label;
    if (n.layer === "claim") return n.fulltext;
    return `Doc ${n.label} · ${(n as any).title}`;
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="verdict-pill"
          style={{ borderColor: c, color: c, background: `${c}1A` }}
        >
          {relLabel(edge.rel)}
        </span>
        <span className="chip">{edge.kind}</span>
        {edge.hard && <span className="chip">hard</span>}
        {edge.own_goal && (
          <span
            className="verdict-pill"
            style={{ borderColor: COLORS.orange, color: COLORS.orange, background: `${COLORS.orange}1A` }}
          >
            own goal
          </span>
        )}
      </div>

      <div className="space-y-2 text-sm">
        <button
          onClick={() => edge.source && onSelect(edge.source)}
          className="block w-full rounded border p-2 text-left hover:bg-bg/40"
          style={{ borderColor: COLORS.hair }}
        >
          <div className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">From</div>
          <p className="text-[13px] text-ink">{fmt(src)}</p>
        </button>
        <div className="text-center font-mono text-[10px] uppercase tracking-widest" style={{ color: c }}>
          ↓ {relLabel(edge.rel)}
        </div>
        <button
          onClick={() => edge.target && onSelect(edge.target)}
          className="block w-full rounded border p-2 text-left hover:bg-bg/40"
          style={{ borderColor: COLORS.hair }}
        >
          <div className="font-mono text-[10px] uppercase tracking-widest text-ink-dim">To</div>
          <p className="text-[13px] text-ink">{fmt(tgt)}</p>
        </button>
      </div>

      {edge.explanation && (
        <div className="rounded border-l-2 p-3 text-[13px] leading-relaxed text-ink" style={{ borderColor: c, background: COLORS.bg }}>
          {edge.explanation}
        </div>
      )}

      {edge.own_goal && (
        <p className="rounded border-l-2 p-3 text-[12px] leading-relaxed text-ink" style={{ borderColor: COLORS.orange, background: `${COLORS.orange}0D` }}>
          <strong className="font-mono uppercase tracking-widest" style={{ color: COLORS.orange }}>
            Own goal.{" "}
          </strong>
          The claimant's own document undermines its pleaded case.
        </p>
      )}
    </div>
  );
}
