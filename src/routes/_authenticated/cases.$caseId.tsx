import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { getCase } from "@/lib/firm.functions";
import type { AppData, DataEdge } from "@/lib/pleading";
import { COLORS, srcId } from "@/lib/pleading";
import PleadingView from "@/components/PleadingView";
import BundleView from "@/components/BundleView";
import Inspector from "@/components/Inspector";
import GraphCanvas from "@/components/GraphCanvas";

type View = "stress" | "coherence" | "graph";

export const Route = createFileRoute("/_authenticated/cases/$caseId")({
  component: CasePage,
});

const CARD_W = 460;
const CARD_H = 540;
const HOLE_R = Math.hypot(CARD_W / 2, CARD_H / 2) + 28;

function CasePage() {
  const { caseId } = Route.useParams();
  const fetchCase = useServerFn(getCase);

  const [row, setRow] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [view, setView] = useState<View>("graph");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<DataEdge | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [popover, setPopover] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    fetchCase({ data: { id: caseId } })
      .then(setRow)
      .catch((e) => setErr(String(e?.message ?? e)));
  }, [caseId, fetchCase]);

  const data: AppData | null = row?.data ?? null;

  const adjacency = useMemo(() => {
    if (!data) return new Map<string, Set<string>>();
    const m = new Map<string, Set<string>>();
    const add = (a: string, b: string) => {
      if (!m.has(a)) m.set(a, new Set());
      m.get(a)!.add(b);
    };
    for (const e of data.edges) {
      const s = srcId(e.source); const t = srcId(e.target);
      add(s, t); add(t, s);
    }
    const expanded = new Map<string, Set<string>>();
    for (const [k, set] of m) {
      const out = new Set<string>(set);
      for (const x of set) { const xs = m.get(x); if (xs) for (const y of xs) out.add(y); }
      expanded.set(k, out);
    }
    return expanded;
  }, [data]);

  const focusId = selectedId ?? hoveredId;
  const highlightedIds = useMemo(
    () => (focusId ? (adjacency.get(focusId) ?? new Set<string>()) : new Set<string>()),
    [focusId, adjacency],
  );

  useEffect(() => {
    if (selectedId || selectedEdge) setInspectorOpen(true);
    else setPopover(null);
  }, [selectedId, selectedEdge]);

  if (err) return <div className="grid min-h-screen place-items-center bg-bg p-6" style={{ color: COLORS.rejected }}>{err}</div>;
  if (!data) return <div className="grid min-h-screen place-items-center bg-bg font-mono text-[11px] text-ink-dim">loading case…</div>;

  const caseTitle = (row.title as string).replace(/\s+v\s+/i, " §V§ ").split("§V§");

  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      <header className="border-b px-5 py-4 sm:px-8" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link to="/cases" className="font-mono text-[10px] uppercase tracking-[0.28em] text-ink-dim hover:text-ink">
              ← All cases
            </Link>
            <h1 className="mt-1.5 font-display text-[22px] leading-tight sm:text-[26px]">
              {caseTitle[0]?.trim()}
              {caseTitle[1] && (<><span className="mx-2 italic font-normal text-ink-dim">v.</span>{caseTitle[1]?.trim()}</>)}
            </h1>
            <div className="mt-1 font-mono text-[11px] tracking-wide text-ink-dim">
              {row.claim_no ?? "—"} &nbsp;·&nbsp; {row.court ?? "—"}
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-2">
            <ViewToggle view={view} setView={(v) => { setView(v); setPopover(null); }} />
            <div className="ml-1 flex flex-wrap gap-2">
              <StatChip label="trial readiness" value={`${data.stats.readiness}/100`}
                color={data.stats.readiness >= 70 ? COLORS.accepted : data.stats.readiness >= 30 ? COLORS.legal : COLORS.rejected} />
              <StatChip label="own goals" value={`${data.stats.own_goal}/10`} color={COLORS.orange} />
              <StatChip label="exposure" value={`${data.stats.exposure_from} → ${data.stats.exposure_to}`} color={COLORS.ink} />
              <StatChip label="docs" value={String(data.stats.docs)} color={COLORS.inkDim} />
            </div>
          </div>
        </div>
      </header>

      {view === "graph" ? (
        <main className="relative flex-1 p-4 sm:p-6">
          <div className="relative h-[calc(100vh-160px)] min-h-[640px] w-full">
            <GraphCanvas
              data={data}
              mode="stress"
              selectedId={selectedId}
              hoveredId={hoveredId}
              onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); }}
              onHover={setHoveredId}
              onSelectEdge={(e) => { setSelectedId(null); setSelectedEdge(e); }}
              centerHole={HOLE_R}
              hideHub
              onNodeClickScreen={(_id, x, y) => setPopover({ x, y })}
            />

            {/* Central Pleading card — the hero piece, sits in the graph's hole. */}
            <div
              className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
              style={{ width: CARD_W, height: CARD_H }}
            >
              <div
                className="pointer-events-auto h-full w-full overflow-hidden rounded-sm border shadow-[0_24px_60px_-30px_rgba(20,17,13,0.45)]"
                style={{ borderColor: COLORS.hair, background: COLORS.panel }}
              >
                <PleadingView
                  data={data}
                  selectedId={selectedId}
                  hoveredId={hoveredId}
                  highlightedIds={highlightedIds}
                  onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); setPopover(null); }}
                  onHover={setHoveredId}
                  mode="stress"
                />
              </div>
            </div>

            {/* Floating Inspector popover, anchored to the clicked node. */}
            {inspectorOpen && popover && (
              <FloatingInspector
                x={popover.x}
                y={popover.y}
                containerSelector
              >
                <Inspector
                  data={data}
                  selectedId={selectedId}
                  selectedEdge={selectedEdge}
                  onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); }}
                  onClose={() => { setSelectedId(null); setSelectedEdge(null); setInspectorOpen(false); setPopover(null); }}
                />
              </FloatingInspector>
            )}

            {/* Edge clicks have no screen coords — fall back to a side drawer. */}
            {inspectorOpen && !popover && (
              <div className="absolute right-4 top-4 z-20 h-[min(560px,calc(100vh-220px))] w-[380px]">
                <Inspector
                  data={data}
                  selectedId={selectedId}
                  selectedEdge={selectedEdge}
                  onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); }}
                  onClose={() => { setSelectedId(null); setSelectedEdge(null); setInspectorOpen(false); }}
                />
              </div>
            )}
          </div>
        </main>
      ) : (
        <main className={`flex-1 grid gap-4 p-4 sm:p-6 ${
          inspectorOpen
            ? "lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.1fr)_minmax(340px,420px)]"
            : "lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]"
        }`}>
          <div className="h-[calc(100vh-200px)] min-h-[560px]">
            <PleadingView
              data={data} selectedId={selectedId} hoveredId={hoveredId} highlightedIds={highlightedIds}
              onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); }} onHover={setHoveredId}
              mode={view}
            />
          </div>
          <div className="h-[calc(100vh-200px)] min-h-[560px]">
            <BundleView
              data={data} selectedId={selectedId} hoveredId={hoveredId} highlightedIds={highlightedIds}
              onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); }} onHover={setHoveredId}
              mode={view}
            />
          </div>
          {inspectorOpen && (
            <div className="h-[calc(100vh-200px)] min-h-[560px]">
              <Inspector
                data={data} selectedId={selectedId} selectedEdge={selectedEdge}
                onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); }}
                onClose={() => { setSelectedId(null); setSelectedEdge(null); setInspectorOpen(false); }}
              />
            </div>
          )}
        </main>
      )}
    </div>
  );
}

function FloatingInspector({
  x, y, children,
}: { x: number; y: number; containerSelector?: boolean; children: React.ReactNode }) {
  // Clamp the popover inside the visible viewport-ish area.
  const W = 360, H = 460;
  const left = Math.max(8, Math.min(x + 18, (typeof window !== "undefined" ? window.innerWidth : 1200) - W - 16));
  const top = Math.max(8, y - 40);
  return (
    <div
      className="absolute z-30 animate-in fade-in zoom-in-95 duration-150"
      style={{ left, top, width: W, height: H }}
    >
      <div
        className="h-full w-full overflow-hidden rounded-sm border shadow-[0_32px_70px_-25px_rgba(20,17,13,0.55)]"
        style={{ borderColor: COLORS.hair, background: COLORS.panel }}
      >
        {children}
      </div>
    </div>
  );
}

function ViewToggle({ view, setView }: { view: View; setView: (v: View) => void }) {
  const opts: Array<{ k: View; label: string }> = [
    { k: "stress", label: "Pleading Stress Test" },
    { k: "coherence", label: "Bundle Coherence" },
    { k: "graph", label: "Graph" },
  ];
  return (
    <div className="inline-flex rounded-sm border p-0.5" style={{ borderColor: COLORS.hair, background: COLORS.panel2 }}>
      {opts.map((o) => {
        const active = view === o.k;
        return (
          <button key={o.k} onClick={() => setView(o.k)}
            className="rounded-sm px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] transition"
            style={{ color: active ? COLORS.panel : COLORS.ink, background: active ? COLORS.ink : "transparent" }}>
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function StatChip({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="inline-flex flex-col rounded-sm border px-3 py-1.5" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
      <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-ink-dim">{label}</span>
      <span className="font-mono text-[13px] font-medium" style={{ color }}>{value}</span>
    </div>
  );
}
