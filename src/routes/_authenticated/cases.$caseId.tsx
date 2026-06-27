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

function CasePage() {
  const { caseId } = Route.useParams();
  // navigate not needed currently
  const fetchCase = useServerFn(getCase);

  const [row, setRow] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [view, setView] = useState<View>("graph");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<DataEdge | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);

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

  useEffect(() => { if (selectedId || selectedEdge) setInspectorOpen(true); }, [selectedId, selectedEdge]);

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
            <ViewToggle view={view} setView={setView} />
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

      <main className={`flex-1 grid gap-4 p-4 sm:p-6 ${
        view === "graph"
          ? (inspectorOpen ? "lg:grid-cols-[minmax(0,1fr)_minmax(340px,420px)]" : "lg:grid-cols-1")
          : (inspectorOpen
              ? "lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.1fr)_minmax(340px,420px)]"
              : "lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]")
      }`}>
        {view === "graph" ? (
          <div className="h-[calc(100vh-200px)] min-h-[560px]">
            <GraphCanvas
              data={data}
              mode={view === "graph" ? "stress" : view}
              selectedId={selectedId}
              hoveredId={hoveredId}
              onSelect={(id) => { setSelectedEdge(null); setSelectedId(id); }}
              onHover={setHoveredId}
              onSelectEdge={(e) => { setSelectedId(null); setSelectedEdge(e); }}
            />
          </div>
        ) : (
          <>
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
          </>
        )}

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
