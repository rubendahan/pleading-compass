import { useEffect, useMemo, useRef, useState } from "react";
import type {
  AppData,
  DataEdge,
  DataNode,
  EdgeRel,
  Mode,
} from "@/lib/pleading";
import { COLORS, edgeColor, nodeColor, srcId } from "@/lib/pleading";

interface Props {
  data: AppData;
  mode: Mode;
  selectedId: string | null;
  hoveredId: string | null;
  onSelect: (id: string | null) => void;
  onHover: (id: string | null) => void;
  onSelectEdge: (e: DataEdge | null) => void;
}

type GraphNode = DataNode & {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
};

interface GraphLink {
  source: GraphNode | string;
  target: GraphNode | string;
  rel: EdgeRel;
  raw: DataEdge;
}

export default function GraphCanvas({
  data,
  mode,
  selectedId,
  hoveredId,
  onSelect,
  onHover,
  onSelectEdge,
}: Props) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const fgRef = useRef<any>(null);
  const [ForceGraph, setForceGraph] = useState<any>(null);
  const [size, setSize] = useState({ w: 600, h: 600 });
  const reducedMotion = useReducedMotion();

  // Load the force graph lib client-side only.
  useEffect(() => {
    let cancelled = false;
    import("react-force-graph-2d").then((mod) => {
      if (!cancelled) setForceGraph(() => mod.default);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Track container size.
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setSize({ w: Math.max(320, r.width), h: Math.max(400, r.height) });
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  // Build filtered graph for the active mode.
  const graph = useMemo(() => {
    const nodes: GraphNode[] = data.nodes.map((n) => ({ ...n }));
    const byId = new Map(nodes.map((n) => [n.id, n] as const));
    let edges = data.edges.slice();
    if (mode === "stress") {
      // Show impact + provenance; fade pure coherence (still include but thin).
      edges = edges.filter((e) =>
        e.kind === "impact" || e.kind === "provenance" || e.kind === "coherence",
      );
    } else {
      // Coherence: foreground claim↔claim, keep impact for grounding, dim provenance.
      edges = edges.filter((e) => e.kind !== "provenance" || e.rel === "asserts");
    }
    // Pin propositions in a vertical column on the left side of the canvas.
    const props = nodes.filter((n) => n.layer === "proposition");
    const colX = -size.w * 0.18;
    const span = Math.min(size.h * 0.85, props.length * 70);
    const step = props.length > 1 ? span / (props.length - 1) : 0;
    props.forEach((p, i) => {
      p.fx = colX;
      p.fy = -span / 2 + i * step;
    });
    const links: GraphLink[] = edges.map((e) => ({
      source: e.source,
      target: e.target,
      rel: e.rel,
      raw: e,
    }));
    return { nodes, links, byId };
  }, [data, mode, size.w, size.h]);

  // Build neighbour index for highlight.
  const neighbours = useMemo(() => {
    const map = new Map<string, Set<string>>();
    const edgeMap = new Map<string, Set<string>>();
    for (const e of data.edges) {
      const s = e.source;
      const t = e.target;
      if (!map.has(s)) map.set(s, new Set());
      if (!map.has(t)) map.set(t, new Set());
      map.get(s)!.add(t);
      map.get(t)!.add(s);
      const key = `${s}__${t}`;
      if (!edgeMap.has(s)) edgeMap.set(s, new Set());
      if (!edgeMap.has(t)) edgeMap.set(t, new Set());
      edgeMap.get(s)!.add(key);
      edgeMap.get(t)!.add(key);
    }
    return { map, edgeMap };
  }, [data.edges]);

  const focusId = hoveredId ?? selectedId;
  const focused = useMemo(() => {
    if (!focusId) return null;
    const set = new Set<string>([focusId]);
    neighbours.map.get(focusId)?.forEach((id) => set.add(id));
    return set;
  }, [focusId, neighbours]);

  // Settle the simulation immediately when reduced motion is on.
  useEffect(() => {
    if (!fgRef.current || !reducedMotion) return;
    try {
      fgRef.current.d3ReheatSimulation();
      for (let i = 0; i < 200; i++) fgRef.current.tickFrame?.();
      fgRef.current.zoomToFit(0, 60);
    } catch {
      /* noop */
    }
  }, [reducedMotion, ForceGraph, mode]);

  // Centre on selection.
  useEffect(() => {
    if (!fgRef.current || !selectedId) return;
    const n: any = graph.nodes.find((x) => x.id === selectedId);
    if (n && typeof n.x === "number" && typeof n.y === "number") {
      fgRef.current.centerAt(n.x, n.y, reducedMotion ? 0 : 600);
    }
  }, [selectedId, graph.nodes, reducedMotion]);

  if (!ForceGraph) {
    return (
      <div
        ref={wrapRef}
        className="relative h-full w-full overflow-hidden rounded-lg border bg-bg"
        style={{ borderColor: COLORS.hair }}
      >
        <div className="absolute inset-0 grid place-items-center text-sm text-ink-dim">
          <div className="font-mono uppercase tracking-widest">initialising graph…</div>
        </div>
      </div>
    );
  }

  // Wheel: scroll the page by default; hold ⌘/Ctrl to zoom the graph.
  const onWheel: React.WheelEventHandler<HTMLDivElement> = (e) => {
    if (!(e.ctrlKey || e.metaKey)) return; // let the page scroll
    e.preventDefault();
    const fg = fgRef.current;
    if (!fg?.zoom) return;
    const current = fg.zoom();
    const factor = Math.exp(-e.deltaY * 0.0015);
    fg.zoom(Math.max(0.3, Math.min(8, current * factor)), 80);
  };

  return (
    <div
      ref={wrapRef}
      className="relative h-full w-full overflow-hidden rounded-sm border"
      style={{ borderColor: COLORS.hair, background: COLORS.panel }}
      onWheel={onWheel}
    >
      <ForceGraph
        ref={fgRef}
        graphData={graph}
        width={size.w}
        height={size.h}
        backgroundColor={COLORS.panel}
        cooldownTicks={reducedMotion ? 0 : 120}
        warmupTicks={reducedMotion ? 200 : 30}
        d3VelocityDecay={0.35}
        linkDirectionalParticles={0}
        nodeRelSize={5}
        enableNodeDrag={true}
        enableZoomInteraction={false}
        enablePanInteraction={true}
        onNodeHover={(n: any) => onHover(n ? n.id : null)}
        onNodeClick={(n: any) => {
          onSelect(n?.id ?? null);
          onSelectEdge(null);
        }}
        onLinkClick={(l: any) => {
          onSelectEdge(l.raw ?? null);
          onSelect(null);
        }}
        onBackgroundClick={() => {
          onSelect(null);
          onSelectEdge(null);
        }}
        linkColor={(l: any) => {
          const dimmed = focused && !isLinkFocused(l, focused);
          const c = edgeColor(l.rel);
          return dimmed ? withAlpha(c, 0.10) : withAlpha(c, l.rel === "asserts" ? 0.45 : 0.78);
        }}
        linkWidth={(l: any) => {
          const isFocus = focused && isLinkFocused(l, focused);
          if (l.raw?.hard) return isFocus ? 2.4 : 1.5;
          if (l.rel === "asserts") return isFocus ? 1.2 : 0.6;
          return isFocus ? 2 : 1.1;
        }}
        linkLineDash={(l: any) => (l.rel === "asserts" ? [2, 3] : null)}
        linkCurvature={(l: any) => (l.rel === "belongs_to" ? 0 : 0.18)}
        linkDirectionalArrowLength={(l: any) =>
          l.rel === "asserts" || l.rel === "belongs_to" ? 0 : 4
        }
        linkDirectionalArrowRelPos={0.85}
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, scale: number) => {
          const isHover = hoveredId === node.id;
          const isSelected = selectedId === node.id;
          const dimmed = focused && !focused.has(node.id);
          const color = nodeColor(node);
          const r =
            node.layer === "proposition"
              ? 11
              : node.layer === "claim"
                ? 6 + Math.min(4, (node.weight ?? 1) * 0.7)
                : 5;

          // Glow on focus.
          if (isHover || isSelected) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 8, 0, 2 * Math.PI);
            ctx.fillStyle = withAlpha(color, 0.18);
            ctx.fill();
          }

          // Body
          ctx.beginPath();
          if (node.layer === "document") {
            // Square for documents
            ctx.rect(node.x - r, node.y - r, r * 2, r * 2);
          } else {
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          }
          ctx.fillStyle = dimmed ? withAlpha(color, 0.18) : color;
          ctx.fill();

          // Brass ring for load-bearing
          if (node.load_bearing) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 2.5, 0, 2 * Math.PI);
            ctx.lineWidth = 1.4;
            ctx.strokeStyle = withAlpha(COLORS.brass, dimmed ? 0.35 : 1);
            ctx.stroke();
          }

          // Selection ring
          if (isSelected) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 5, 0, 2 * Math.PI);
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = COLORS.accent;
            ctx.stroke();
          }

          // Label
          const showLabel =
            node.layer === "proposition" || isHover || isSelected || scale > 1.8;
          if (showLabel) {
            ctx.font = `${node.layer === "proposition" ? 600 : 500} ${
              node.layer === "proposition" ? 11 : 10
            }px Inter, sans-serif`;
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            const text =
              node.layer === "proposition"
                ? node.label
                : node.layer === "document"
                  ? `${node.label} · ${truncate(node.title, 28)}`
                  : truncate(node.fulltext ?? node.label, 36);
            const pad = 4;
            const x = node.x + r + 6;
            const y = node.y;
            const w = ctx.measureText(text).width;
            ctx.fillStyle = withAlpha(COLORS.panel, dimmed ? 0.5 : 0.85);
            ctx.fillRect(x - pad, y - 8, w + pad * 2, 16);
            ctx.fillStyle = dimmed ? COLORS.inkDim : COLORS.ink;
            ctx.fillText(text, x, y);
          }
        }}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const r =
            node.layer === "proposition"
              ? 14
              : node.layer === "claim"
                ? 9
                : 8;
          ctx.fillStyle = color;
          if (node.layer === "document") {
            ctx.fillRect(node.x - r, node.y - r, r * 2, r * 2);
          } else {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
            ctx.fill();
          }
        }}
      />
      <Legend mode={mode} />
    </div>
  );
}

function isLinkFocused(l: any, focused: Set<string>): boolean {
  const s = srcId(l.source);
  const t = srcId(l.target);
  return focused.has(s) && focused.has(t);
}

function withAlpha(hex: string, a: number): string {
  // hex #RRGGBB → rgba()
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

function truncate(s: string, n: number): string {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const h = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener?.("change", h);
    return () => mq.removeEventListener?.("change", h);
  }, []);
  return reduced;
}

function Legend({ mode }: { mode: Mode }) {
  const items: Array<[string, string]> = [
    ["supports", COLORS.accepted],
    ["contradicts", COLORS.rejected],
    ["attacks / supersedes", COLORS.orange],
    ["caps / qualifies / legal bar", COLORS.legal],
    ["asserts (provenance)", COLORS.accent],
  ];
  return (
    <div
      className="pointer-events-none absolute bottom-3 right-3 rounded-md border px-3 py-2 text-[10px] uppercase tracking-widest text-ink-dim backdrop-blur"
      style={{
        borderColor: COLORS.hair,
        background: withAlpha(COLORS.panel, 0.7),
        fontFamily: "JetBrains Mono, monospace",
      }}
    >
      <div className="mb-1 text-ink">{mode === "stress" ? "Stress test" : "Bundle coherence"}</div>
      {items.map(([k, c]) => (
        <div key={k} className="flex items-center gap-2 leading-5">
          <span className="inline-block h-[2px] w-5" style={{ background: c }} />
          <span>{k}</span>
        </div>
      ))}
    </div>
  );
}
