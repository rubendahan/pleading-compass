import { useEffect, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import type { AppData, ClaimNode, DataEdge, DataNode, PropositionNode } from "@/lib/pleading";
import { COLORS, edgeColor, relLabel, verdictColor } from "@/lib/pleading";
import { summariseNode } from "@/lib/summary.functions";

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
        <SectionHeading>AI bundle note</SectionHeading>
        <button
          onClick={run}
          disabled={state.loading}
          className="rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-widest transition hover:bg-bg/40 disabled:opacity-50"
          style={{ borderColor: COLORS.hair, color: COLORS.ink }}
        >
          {state.loading ? "drafting…" : state.text ? "regenerate" : "generate"}
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
          One-paragraph forensic note grounded in this node and its relations.
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
        <li>· proposition → why it stands or falls</li>
        <li>· claim → verbatim quote + anchor</li>
        <li>· edge → relation and explanation</li>
      </ul>
      <p className="mt-6 text-[12px] italic text-ink-dim">
        "The strongest coherent bundle story suggests…" — lawyer review required.
      </p>
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

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <VerdictPill verdict={node.verdict} />
        <OverlayChip overlay={node.overlay} />
      </div>
      <p className="text-sm leading-relaxed text-ink">{node.text}</p>
      <ReadinessBar value={node.readiness} />

      {cluster && (
        <div>
          <SectionHeading>Coherent story — {cluster.issue.toLowerCase()}</SectionHeading>
          <ul className="space-y-1.5 text-sm leading-relaxed text-ink-dim">
            {cluster.story.map((s, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-1 inline-block h-1 w-1 shrink-0 rounded-full" style={{ background: COLORS.accent }} />
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {impact && (
        <div className="rounded-md border p-3" style={{ borderColor: COLORS.hair, background: `${COLORS.rejected}0D` }}>
          <SectionHeading>Impact</SectionHeading>
          <p className="text-[13px] leading-relaxed text-ink">{impact}</p>
        </div>
      )}

      {cluster && cluster.amendments.length > 0 && (
        <div>
          <SectionHeading>Suggested amendments</SectionHeading>
          <ul className="space-y-2 text-sm leading-relaxed text-ink">
            {cluster.amendments.map((a, i) => (
              <li
                key={i}
                className="rounded border-l-2 pl-3"
                style={{ borderColor: COLORS.legal }}
              >
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <SectionHeading>Claims targeting this proposition ({claims.length})</SectionHeading>
        <ul className="space-y-2">
          {claims.map((c) => (
            <ClaimRow key={c.id} claim={c} onSelect={onSelect} />
          ))}
        </ul>
      </div>

      <p className="rounded border-l-2 pl-3 text-[11px] italic leading-relaxed text-ink-dim" style={{ borderColor: COLORS.accent }}>
        Lawyer review required. The console reports coherence in this bundle — it does not
        decide the case.
      </p>
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
          <div className="mt-1 font-mono text-[10px] text-ink-dim">{claim.anchor}</div>
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

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <VerdictPill verdict={node.verdict} />
        <span className="chip">{node.polarity}</span>
        <span className="chip">{node.source_type.replace(/_/g, " ")}</span>
        <span className="chip">weight {node.weight.toFixed(1)}</span>
        {node.load_bearing && (
          <span
            className="verdict-pill"
            style={{ borderColor: COLORS.brass, color: COLORS.brass, background: `${COLORS.brass}1A` }}
          >
            load-bearing
          </span>
        )}
        {node.single_source && (
          <span
            className="verdict-pill"
            style={{ borderColor: COLORS.brass, color: COLORS.brass, background: `${COLORS.brass}1A` }}
          >
            single source
          </span>
        )}
      </div>

      <p className="text-sm leading-relaxed text-ink">{node.fulltext}</p>

      {(node.load_bearing || node.single_source) && (
        <div className="rounded-md border-l-2 pl-3 text-[12px] leading-relaxed text-ink" style={{ borderColor: COLORS.brass, background: `${COLORS.brass}0D` }}>
          <span className="font-mono uppercase tracking-widest" style={{ color: COLORS.brass }}>
            Load-bearing —{" "}
          </span>
          this point rests on a single source; discredit it and it collapses.
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

      {node.quote ? (
        <div>
          <SectionHeading>
            Verbatim quote {node.anchor && <span style={{ color: COLORS.accent }}>· {node.anchor}</span>}
          </SectionHeading>
          <blockquote
            className="rounded border-l-2 p-3 font-mono text-[12px] leading-relaxed text-ink"
            style={{ borderColor: c, background: COLORS.bg }}
          >
            “{node.quote}”
          </blockquote>
        </div>
      ) : (
        <div className="rounded border p-3 text-[12px] italic text-ink-dim" style={{ borderColor: COLORS.hair }}>
          No quote-grounded support found in this bundle.
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
                    <span className="text-ink">
                      {(doc as any).title}
                    </span>
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
          ? `Doc ${(other as any).label} — ${(other as any).title}`
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
    return `Doc ${n.label} — ${(n as any).title}`;
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
            Own goal —{" "}
          </strong>
          the claimant's own document undermines its pleaded case.
        </p>
      )}
    </div>
  );
}
