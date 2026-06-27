import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { getCase } from "@/lib/firm.functions";
import type { AppData, DataEdge } from "@/lib/pleading";
import { COLORS, srcId } from "@/lib/pleading";
import PleadingView from "@/components/PleadingView";
import BundleView from "@/components/BundleView";
import Inspector from "@/components/Inspector";
import GraphCanvas from "@/components/GraphCanvas";
import BundlePiecePopover from "@/components/BundlePiecePopover";

type View = "stress" | "coherence" | "graph";

export const Route = createFileRoute("/_authenticated/cases/$caseId")({
  component: CasePage,
});

const CARD_W = 760;
const CARD_H = 680;

function CasePage() {
  const { caseId } = Route.useParams();
  const fetchCase = useServerFn(getCase);

  const [row, setRow] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [view, setView] = useState<View>("graph");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Inspector can be focused on a different node than the main selection — e.g.
  // when clicking a pleading claim, the inspector follows the scrolled-to bundle item.
  const [inspectorId, setInspectorId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<DataEdge | null>(null);

  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [popover, setPopover] = useState<{ id: string; x: number; y: number } | null>(null);
  const [pleadingOffset, setPleadingOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const pleadingDragRef = useRef<{ ox: number; oy: number; sx: number; sy: number } | null>(null);
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const [graphSize, setGraphSize] = useState<{ w: number; h: number }>({ w: 1000, h: 700 });
  const graphApi = useRef<{ focusNodes: (ids: string[]) => void } | null>(null);


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

  // In graph view, node clicks open the floating popover (inspector stays manual).
  // In dual-pane views (stress / coherence), selecting a node opens the inspector.
  useEffect(() => {
    if (selectedEdge) setInspectorOpen(true);
    else if (selectedId && view !== "graph") setInspectorOpen(true);
    else if (!selectedId && !selectedEdge) { setInspectorOpen(false); setPopover(null); }
  }, [selectedId, selectedEdge, view]);


  // Track graph container size for popover clamping.
  useEffect(() => {
    if (!graphContainerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setGraphSize({ w: r.width, h: r.height });
    });
    ro.observe(graphContainerRef.current);
    return () => ro.disconnect();
  }, []);

  // Drag the central pleading card by its header.
  useEffect(() => {
    function onMove(e: PointerEvent) {
      const d = pleadingDragRef.current;
      if (!d) return;
      setPleadingOffset({ x: d.ox + (e.clientX - d.sx), y: d.oy + (e.clientY - d.sy) });
    }
    function onUp() { pleadingDragRef.current = null; }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, []);


  // Cross-pane interaction: when ANY node is selected, focus the graph on its
  // supporting/contradicting evidence and scroll the bundle pane to the most
  // interesting related item.
  useEffect(() => {
    if (!data || !selectedId) return;
    const node = data.nodes.find((n) => n.id === selectedId);
    if (!node) return;

    // Compute candidate "bundle targets" (non-pleading, non-proposition nodes).
    const isPleadingClaim = (n: any) => n?.layer === "claim" && n.polarity === "pleading";
    const isBundleNode = (n: any) =>
      n && (n.layer === "document" || (n.layer === "claim" && n.polarity !== "pleading"));

    let targetIds: string[] = [];

    if (isBundleNode(node)) {
      // Already a bundle node: scroll right to it.
      targetIds = [node.id];
    } else {
      // Proposition or pleading-claim: collect directly linked bundle nodes.
      const direct = new Set<string>();
      for (const e of data.edges) {
        const s = srcId(e.source); const t = srcId(e.target);
        const other = s === selectedId ? t : t === selectedId ? s : null;
        if (!other) continue;
        const on = data.nodes.find((n) => n.id === other);
        if (isBundleNode(on)) direct.add(other);
      }
      // Hop through pleading-claims (proposition → pleading-claim → bundle).
      if (direct.size === 0) {
        for (const e of data.edges) {
          const s = srcId(e.source); const t = srcId(e.target);
          const mid = s === selectedId ? t : t === selectedId ? s : null;
          if (!mid) continue;
          const midNode = data.nodes.find((n) => n.id === mid);
          if (!isPleadingClaim(midNode)) continue;
          for (const e2 of data.edges) {
            const s2 = srcId(e2.source); const t2 = srcId(e2.target);
            const other = s2 === mid ? t2 : t2 === mid ? s2 : null;
            if (!other) continue;
            const on = data.nodes.find((n) => n.id === other);
            if (isBundleNode(on)) direct.add(other);
          }
        }
      }
      // Last resort: broader adjacency, filtered to bundle.
      if (direct.size === 0) {
        for (const id of adjacency.get(selectedId) ?? []) {
          const on = data.nodes.find((n) => n.id === id);
          if (isBundleNode(on)) direct.add(id);
        }
      }

      // Rank: load-bearing > contradicts/supports verdict > docs > anything.
      const score = (id: string) => {
        const n: any = data.nodes.find((x) => x.id === id);
        if (!n) return 0;
        let s = 0;
        if (n.load_bearing) s += 10;
        if (n.verdict === "CONTRADICTED" || n.verdict === "SUPPORTED") s += 5;
        if (n.layer === "document") s += 1;
        return s;
      };
      targetIds = Array.from(direct).sort((a, b) => score(b) - score(a));
    }

    if (!targetIds.length) {
      setInspectorId(selectedId);
      return;
    }

    const first = targetIds[0];
    // Inspector follows the scrolled-to / focused bundle target, while the
    // pleading-side selection stays highlighted in the pleading view.
    setInspectorId(isBundleNode(node) ? node.id : first);

    if (view === "graph") {
      graphApi.current?.focusNodes(targetIds);
    } else {
      requestAnimationFrame(() => {
        const el = document.querySelector(`[data-bundle-id="${CSS.escape(first)}"]`);
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
  }, [selectedId, data, adjacency, view]);

  // Clear inspector focus when nothing is selected.
  useEffect(() => {
    if (!selectedId) setInspectorId(null);
  }, [selectedId]);



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
          <div ref={graphContainerRef} className="relative h-[calc(100vh-160px)] min-h-[640px] w-full">
            <GraphCanvas
              data={data}
              mode="stress"
              selectedId={selectedId}
              hoveredId={hoveredId}
              onSelect={(id) => {
                setSelectedEdge(null);
                setSelectedId(id);
                if (!id) setPopover(null);
              }}
              onHover={setHoveredId}
              onSelectEdge={(e) => { setSelectedId(null); setSelectedEdge(e); }}
              centerHoleRect={{
                rx: Math.min(CARD_W, graphSize.w - 80) / 2 + 24,
                ry: Math.min(CARD_H, graphSize.h - 80) / 2 + 24,
              }}
              hideHub
              onNodeClickScreen={(id, x, y) => setPopover({ id, x, y })}
              apiRef={graphApi}
            />

            {/* Central Pleading card — draggable hero piece. */}
            <div
              className="pointer-events-none absolute left-1/2 top-1/2"
              style={{
                transform: `translate(calc(-50% + ${pleadingOffset.x}px), calc(-50% + ${pleadingOffset.y}px))`,
                width: `min(${CARD_W}px, calc(100vw - ${inspectorOpen ? 480 : 120}px))`,
                height: `min(${CARD_H}px, calc(100vh - 200px))`,
              }}
            >
              <div
                className="pointer-events-auto relative flex h-full w-full flex-col overflow-hidden rounded-sm border shadow-[0_24px_60px_-30px_rgba(20,17,13,0.45)]"
                style={{ borderColor: COLORS.hair, background: COLORS.panel }}
              >
                {/* Drag handle bar at the very top of the card. */}
                <div
                  className="flex items-center justify-between gap-2 border-b px-3 py-1.5 cursor-grab active:cursor-grabbing select-none"
                  style={{ borderColor: COLORS.hair, background: COLORS.panel2 }}
                  onPointerDown={(e) => {
                    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
                    pleadingDragRef.current = {
                      ox: pleadingOffset.x, oy: pleadingOffset.y,
                      sx: e.clientX, sy: e.clientY,
                    };
                  }}
                >
                  <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-ink-dim">
                    ⋮⋮ drag pleading
                  </span>
                  {(pleadingOffset.x !== 0 || pleadingOffset.y !== 0) && (
                    <button
                      onClick={() => setPleadingOffset({ x: 0, y: 0 })}
                      className="rounded-sm border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-ink-dim hover:text-ink"
                      style={{ borderColor: COLORS.hair }}
                    >
                      recentre
                    </button>
                  )}
                </div>
                <div className="flex-1 overflow-hidden">
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
            </div>

            {/* Floating bundle-piece popover anchored at the clicked node. */}
            {popover && (
              <BundlePiecePopover
                data={data}
                nodeId={popover.id}
                anchor={{ x: popover.x, y: popover.y }}
                container={{ w: graphSize.w, h: graphSize.h }}
                onClose={() => { setPopover(null); setSelectedId(null); }}
                onSelect={(id) => { setSelectedId(id); }}
                onOpenInspector={() => setInspectorOpen(true)}
              />
            )}

            {/* Inspector as a stable right-side drawer — opens on demand. */}
            {inspectorOpen && (
              <div
                className="absolute right-4 top-4 bottom-4 z-20 w-[420px] max-w-[calc(100vw-32px)] animate-in slide-in-from-right-4 fade-in duration-150"
              >
                <div
                  className="h-full w-full overflow-hidden rounded-sm border shadow-[0_32px_70px_-25px_rgba(20,17,13,0.55)]"
                  style={{ borderColor: COLORS.hair, background: COLORS.panel }}
                >
                  <Inspector caseId={caseId}
                    data={data}
                    selectedId={selectedId}
                    selectedEdge={selectedEdge}
                    onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); }}
                    onClose={() => { setSelectedEdge(null); setInspectorOpen(false); }}
                  />
                </div>
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
              <Inspector caseId={caseId}
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
