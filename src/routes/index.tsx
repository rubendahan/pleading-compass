import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import type { AppData, DataEdge, Mode } from "@/lib/pleading";
import { COLORS, srcId } from "@/lib/pleading";
import Inspector from "@/components/Inspector";
import PleadingView from "@/components/PleadingView";
import BundleView from "@/components/BundleView";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Pleading-to-Proof — Coherence Console" },
      {
        name: "description",
        content:
          "Drag-and-drop trial bundle on one side; the pleading on the other. See which allegations stand, which fall, and why.",
      },
      { property: "og:title", content: "Pleading-to-Proof — Coherence Console" },
      {
        property: "og:description",
        content: "Bundle of evidence on one side, pleading on the other — connections drawn.",
      },
    ],
  }),
  component: Page,
});

function Page() {
  const [data, setData] = useState<AppData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("stress");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<DataEdge | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [scaleOpen, setScaleOpen] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);

  useEffect(() => {
    fetch("/data.json")
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, []);

  // Build adjacency: for any focus id, return the set of ids transitively
  // linked through edges (1 hop direct, 2 hops for pleading↔doc via claims).
  const adjacency = useMemo(() => {
    if (!data) return new Map<string, Set<string>>();
    const m = new Map<string, Set<string>>();
    const add = (a: string, b: string) => {
      if (!m.has(a)) m.set(a, new Set());
      m.get(a)!.add(b);
    };
    for (const e of data.edges) {
      const s = srcId(e.source);
      const t = srcId(e.target);
      add(s, t);
      add(t, s);
    }
    // Expand once more: include neighbours-of-neighbours, so clicking a prop
    // also lights up the documents that source the contradicting claims.
    const expanded = new Map<string, Set<string>>();
    for (const [k, set] of m) {
      const out = new Set<string>(set);
      for (const x of set) {
        const xs = m.get(x);
        if (xs) for (const y of xs) out.add(y);
      }
      expanded.set(k, out);
    }
    return expanded;
  }, [data]);

  const focusId = selectedId ?? hoveredId;
  const highlightedIds = useMemo(() => {
    if (!focusId) return new Set<string>();
    return adjacency.get(focusId) ?? new Set<string>();
  }, [focusId, adjacency]);

  // Auto-open inspector when something is selected.
  useEffect(() => {
    if (selectedId || selectedEdge) setInspectorOpen(true);
  }, [selectedId, selectedEdge]);

  if (err) {
    return (
      <div className="grid min-h-screen place-items-center bg-bg p-6 text-rejected">
        Failed to load case data: {err}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="grid min-h-screen place-items-center bg-bg">
        <div className="font-mono text-xs uppercase tracking-[0.3em] text-ink-dim">
          loading case file…
        </div>
      </div>
    );
  }

  const caseTitle = data.meta.case.replace(/\s+v\s+/i, " §V§ ").split("§V§");

  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      <header
        className="border-b px-5 py-4 sm:px-8"
        style={{ borderColor: COLORS.hair, background: COLORS.panel }}
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-ink-dim">
              <span
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: COLORS.ink }}
              />
              Pleading-to-Proof · Coherence Console
            </div>
            <h1 className="mt-1.5 font-display text-[24px] leading-tight text-ink sm:text-[28px]">
              {caseTitle[0]?.trim()}
              <span className="mx-2 italic font-normal text-ink-dim">v.</span>
              {caseTitle[1]?.trim()}
            </h1>
            <div className="mt-1 font-mono text-[11px] tracking-wide text-ink-dim">
              {data.meta.claim_no} &nbsp;·&nbsp; {data.meta.court}
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-2">
            <ModeToggle mode={mode} setMode={setMode} />
            <div className="ml-1 flex flex-wrap gap-2">
              <StatChip
                label="trial readiness"
                value={`${data.stats.readiness}/100`}
                color={
                  data.stats.readiness >= 70
                    ? COLORS.accepted
                    : data.stats.readiness >= 30
                      ? COLORS.legal
                      : COLORS.rejected
                }
              />
              <StatChip
                label="own goals"
                value={`${data.stats.own_goal}/10`}
                color={COLORS.orange}
              />
              <StatChip
                label="exposure"
                value={`${data.stats.exposure_from} → ${data.stats.exposure_to}`}
                color={COLORS.ink}
              />
              <StatChip label="docs" value={String(data.stats.docs)} color={COLORS.inkDim} />
            </div>
          </div>
        </div>
      </header>

      <main
        className={`flex-1 grid gap-4 p-4 sm:p-6 ${
          inspectorOpen
            ? "lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.1fr)_minmax(340px,420px)]"
            : "lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]"
        }`}
      >
        <div className="h-[calc(100vh-200px)] min-h-[560px] lg:h-auto">
          <PleadingView
            data={data}
            selectedId={selectedId}
            hoveredId={hoveredId}
            highlightedIds={highlightedIds}
            onSelect={(id) => {
              setSelectedEdge(null);
              setSelectedId(id);
            }}
            onHover={setHoveredId}
          />
        </div>

        <div className="h-[calc(100vh-200px)] min-h-[560px] lg:h-auto">
          <BundleView
            data={data}
            selectedId={selectedId}
            hoveredId={hoveredId}
            highlightedIds={highlightedIds}
            onSelect={(id) => {
              setSelectedEdge(null);
              setSelectedId(id);
            }}
            onHover={setHoveredId}
          />
        </div>

        {inspectorOpen && (
          <div className="h-[calc(100vh-200px)] min-h-[560px] lg:h-auto">
            <Inspector
              data={data}
              selectedId={selectedId}
              selectedEdge={selectedEdge}
              onSelect={(id) => {
                setSelectedEdge(null);
                setSelectedId(id);
              }}
              onClose={() => {
                setSelectedId(null);
                setSelectedEdge(null);
                setInspectorOpen(false);
              }}
            />
          </div>
        )}
      </main>

      {!inspectorOpen && (
        <button
          type="button"
          onClick={() => setInspectorOpen(true)}
          className="fixed bottom-20 right-4 z-10 hidden rounded-sm border px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em] shadow-sm lg:inline-flex"
          style={{ borderColor: COLORS.hair, background: COLORS.panel, color: COLORS.ink }}
        >
          Open inspector
        </button>
      )}

      <footer
        className="border-t px-4 py-3 sm:px-6"
        style={{ borderColor: COLORS.hair, background: COLORS.panel }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            onClick={() => setScaleOpen((s) => !s)}
            className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-ink-dim hover:text-ink"
          >
            <span style={{ color: COLORS.accent }}>{scaleOpen ? "▾" : "▸"}</span>
            How this scales
          </button>
          <div className="hidden items-center gap-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-dim sm:flex">
            <Legend swatch={COLORS.accepted} label="supported" />
            <Legend swatch={COLORS.rejected} label="contradicted" />
            <Legend swatch={COLORS.legal} label="legal overlay" />
            <Legend swatch={COLORS.absence} label="not addressed" />
          </div>
        </div>
        {scaleOpen && (
          <div className="mt-3 max-w-3xl space-y-2 text-[12px] leading-relaxed text-ink-dim">
            <p>
              This view is{" "}
              <span className="text-ink">pleading-centred and issue-local</span>, not one
              global graph of every case.
            </p>
            <p>
              It is downstream of retrieval / TAR — the bundle here is already triaged. The
              console reasons over the surfaced top-k evidence for each pleaded issue.
            </p>
            <p>
              Cost scales with{" "}
              <span className="font-mono text-ink">pleaded issues × top-k evidence</span>,
              not with bundle size.
            </p>
            <p className="italic">
              Rejected by stronger quote-grounded evidence ≠ the witness is lying. Lawyer
              review required. {mode === "coherence" ? "(Coherence mode)" : ""}
            </p>
          </div>
        )}
      </footer>
    </div>
  );
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block h-2 w-2 rounded-sm"
        style={{ background: swatch }}
        aria-hidden
      />
      {label}
    </span>
  );
}

function ModeToggle({ mode, setMode }: { mode: Mode; setMode: (m: Mode) => void }) {
  const opts: Array<{ k: Mode; label: string }> = [
    { k: "stress", label: "Pleading Stress Test" },
    { k: "coherence", label: "Bundle Coherence" },
  ];
  return (
    <div
      className="inline-flex rounded-sm border p-0.5"
      style={{ borderColor: COLORS.hair, background: COLORS.panel2 }}
    >
      {opts.map((o) => {
        const active = mode === o.k;
        return (
          <button
            key={o.k}
            onClick={() => setMode(o.k)}
            className="rounded-sm px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] transition"
            style={{
              color: active ? COLORS.panel : COLORS.ink,
              background: active ? COLORS.ink : "transparent",
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function StatChip({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div
      className="inline-flex flex-col rounded-sm border px-3 py-1.5"
      style={{ borderColor: COLORS.hair, background: COLORS.panel }}
    >
      <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-ink-dim">
        {label}
      </span>
      <span className="font-mono text-[13px] font-medium" style={{ color }}>
        {value}
      </span>
    </div>
  );
}
