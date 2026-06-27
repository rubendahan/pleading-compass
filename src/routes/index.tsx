import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type { AppData, Mode, PropositionNode } from "@/lib/pleading";
import { COLORS, verdictColor } from "@/lib/pleading";
import Inspector from "@/components/Inspector";

const GraphCanvas = lazy(() => import("@/components/GraphCanvas"));

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Pleading-to-Proof — Coherence Console" },
      {
        name: "description",
        content:
          "An Obsidian-style coherence console for litigation pleadings: see which allegations stand, which fall, and why.",
      },
      { property: "og:title", content: "Pleading-to-Proof — Coherence Console" },
      {
        property: "og:description",
        content: "Pleading at the centre; evidence orbits. Colour-coded by judgment.",
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
  const [selectedEdge, setSelectedEdge] = useState<AppData["edges"][number] | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [scaleOpen, setScaleOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetch("/data.json")
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, []);

  const propositions = useMemo<PropositionNode[]>(
    () =>
      data
        ? (data.nodes.filter((n) => n.layer === "proposition") as PropositionNode[])
        : [],
    [data],
  );

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

  const caseTitle = data.meta.case
    .replace(/\s+v\s+/i, " §V§ ")
    .split("§V§");

  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      {/* Header */}
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
            <h1 className="mt-1.5 font-display text-[26px] leading-tight text-ink sm:text-[30px]">
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
              <StatChip label="claims" value={String(data.stats.claims)} color={COLORS.inkDim} />
            </div>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <main className="flex-1 grid gap-4 p-4 sm:p-6 lg:grid-cols-[minmax(320px,400px)_1fr_minmax(320px,420px)]">
        {/* Pleading column */}
        <section
          className="flex h-[calc(100vh-200px)] min-h-[520px] flex-col overflow-hidden rounded-sm border lg:h-auto"
          style={{ borderColor: COLORS.hair, background: COLORS.panel }}
        >
          <div className="border-b px-5 py-4" style={{ borderColor: COLORS.hair }}>
            <div className="rule-label">Particulars of Claim</div>
            <h2 className="mt-1 font-display text-[18px] italic">Pleaded allegations</h2>
            <p className="mt-1.5 text-[12px] leading-relaxed text-ink-dim">
              Each block is a proposition. Select one to see what stands or falls, and why.
            </p>
          </div>
          <ol className="flex-1 overflow-y-auto px-4 py-4">
            {propositions.map((p) => {
              const c = verdictColor(p.verdict);
              const active = selectedId === p.id;
              return (
                <li key={p.id} className="mb-2.5">
                  <button
                    onClick={() => {
                      setSelectedEdge(null);
                      setSelectedId(p.id);
                    }}
                    onMouseEnter={() => setHoveredId(p.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    className="group block w-full rounded-sm border p-3.5 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
                    style={{
                      borderColor: active ? COLORS.ink : COLORS.hair,
                      borderLeftWidth: 3,
                      borderLeftColor: c,
                      background: active ? COLORS.panel2 : COLORS.panel,
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className="font-mono text-[11px] uppercase tracking-[0.18em]"
                        style={{ color: COLORS.ink }}
                      >
                        {p.label}
                      </span>
                      <span
                        className="verdict-pill"
                        style={{
                          borderColor: c,
                          color: c,
                          background: `${c}12`,
                        }}
                      >
                        {p.verdict.replace("_", " ")}
                      </span>
                    </div>
                    <p className="mt-2 font-display text-[14px] leading-snug text-ink">
                      {p.text}
                    </p>
                    {p.overlay && p.overlay !== "NONE" && (
                      <div
                        className="mt-2.5 inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest"
                        style={{ borderColor: COLORS.legal, color: COLORS.legal }}
                      >
                        Legal · {p.overlay.replace(/_/g, " ").toLowerCase()}
                      </div>
                    )}
                  </button>
                </li>
              );
            })}
          </ol>
        </section>

        {/* Graph */}
        <section
          className="h-[calc(100vh-200px)] min-h-[520px] lg:h-auto"
          style={{ minHeight: 520 }}
        >
          {mounted ? (
            <Suspense
              fallback={
                <div
                  className="grid h-full place-items-center rounded-sm border text-xs font-mono uppercase tracking-widest text-ink-dim"
                  style={{ borderColor: COLORS.hair, background: COLORS.panel }}
                >
                  loading graph…
                </div>
              }
            >
              <GraphCanvas
                data={data}
                mode={mode}
                selectedId={selectedId}
                hoveredId={hoveredId}
                onSelect={(id) => {
                  setSelectedEdge(null);
                  setSelectedId(id);
                }}
                onHover={setHoveredId}
                onSelectEdge={(e) => {
                  setSelectedId(null);
                  setSelectedEdge(e);
                }}
              />
            </Suspense>
          ) : (
            <div
              className="grid h-full place-items-center rounded-sm border"
              style={{ borderColor: COLORS.hair, background: COLORS.panel }}
            />
          )}
        </section>

        {/* Inspector */}
        <section className="h-[calc(100vh-200px)] min-h-[520px] lg:h-auto" style={{ minHeight: 520 }}>
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
            }}
          />
        </section>
      </main>

      {/* Honesty footer */}
      <footer
        className="border-t px-4 py-3 sm:px-6"
        style={{ borderColor: COLORS.hair, background: COLORS.panel }}
      >
        <button
          onClick={() => setScaleOpen((s) => !s)}
          className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-ink-dim hover:text-ink"
        >
          <span style={{ color: COLORS.accent }}>{scaleOpen ? "▾" : "▸"}</span>
          How this scales
        </button>
        {scaleOpen && (
          <div className="mt-3 max-w-3xl space-y-2 text-[12px] leading-relaxed text-ink-dim">
            <p>
              This view is <span className="text-ink">pleading-centred and issue-local</span>,
              not one global graph of every case.
            </p>
            <p>
              It is downstream of retrieval / TAR — the bundle here is already triaged. The
              console reasons over the surfaced top-k evidence for each pleaded issue.
            </p>
            <p>
              Cost scales with{" "}
              <span className="font-mono text-ink">pleaded issues × top-k evidence</span>, not
              with bundle size.
            </p>
            <p className="italic">
              Rejected by stronger quote-grounded evidence ≠ the witness is lying. Lawyer
              review required.
            </p>
          </div>
        )}
      </footer>
    </div>
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
