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
  /** Pixel radius of an empty circular hole at the centre (for an overlay card). */
  centerHole?: number;
  /** Elliptical hole (overrides centerHole). Pushes free nodes outside the ellipse. */
  centerHoleRect?: { rx: number; ry: number };
  /** Hide the default "PLEADING" hub disc (use when an overlay card sits there). */
  hideHub?: boolean;
  /** Called when a node is clicked, with container-relative pixel coords. */
  onNodeClickScreen?: (id: string, x: number, y: number) => void;
  /** Imperative API ref: caller can pan/zoom to a set of node ids, with an optional
   * horizontal screen bias (px) so the nodes land to the right of a centre card. */
  apiRef?: React.MutableRefObject<{ focusNodes: (ids: string[], biasX?: number) => void } | null>;

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
  centerHole = 0,
  centerHoleRect,
  hideHub = false,
  onNodeClickScreen,
  apiRef,
}: Props) {

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const fgRef = useRef<any>(null);
  const [ForceGraph, setForceGraph] = useState<any>(null);
  const [size, setSize] = useState({ w: 600, h: 600 });
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    let cancelled = false;
    import("react-force-graph-2d").then((mod) => {
      if (!cancelled) setForceGraph(() => mod.default);
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setSize({ w: Math.max(320, r.width), h: Math.max(400, r.height) });
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  // Compute geometry: hole shape for centre card, ring radius for propositions.
  const geom = useMemo(() => {
    const minDim = Math.min(size.w, size.h);
    const rx = centerHoleRect?.rx ?? (centerHole > 0 ? centerHole : Math.max(90, minDim * 0.16));
    const ry = centerHoleRect?.ry ?? (centerHole > 0 ? centerHole : Math.max(90, minDim * 0.16));
    const hole = Math.min(rx, ry);
    // Place propositions on an ellipse just outside the card.
    const ringRx = rx + 32;
    const ringRy = ry + 32;
    return { hole, rx, ry, ringRx, ringRy };
  }, [size.w, size.h, centerHole, centerHoleRect]);

  const graph = useMemo(() => {
    const nodes: GraphNode[] = data.nodes.map((n) => ({ ...n }));
    let edges = data.edges.slice();
    if (mode === "stress") {
      edges = edges.filter((e) =>
        e.kind === "impact" || e.kind === "provenance" || e.kind === "coherence",
      );
    } else {
      edges = edges.filter((e) => e.kind !== "provenance" || e.rel === "asserts");
    }
    const props = nodes.filter((n) => n.layer === "proposition");
    props.forEach((p, i) => {
      const a = (i / props.length) * Math.PI * 2 - Math.PI / 2;
      p.fx = Math.cos(a) * geom.ringRx;
      p.fy = Math.sin(a) * geom.ringRy;
    });
    const links: GraphLink[] = edges.map((e) => ({
      source: e.source, target: e.target, rel: e.rel, raw: e,
    }));
    return { nodes, links };
  }, [data, mode, geom.ringRx, geom.ringRy]);

  // Apply a centre-hole repulsion + tighter bounds so nodes stay on-screen.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    try {
      const sim = fg.d3Force ? fg : null;
      if (!sim) return;
      fg.d3Force("charge")?.strength(-70).distanceMax(260);
      // Elliptical hole repulsion.
      const holeForce = (alpha: number) => {
        const rx = geom.rx + 18;
        const ry = geom.ry + 18;
        for (const n of graph.nodes as any[]) {
          if (n.layer === "proposition") continue;
          const x = n.x ?? 0, y = n.y ?? 0;
          const nx = x / rx, ny = y / ry;
          const d = Math.sqrt(nx * nx + ny * ny) || 0.0001;
          if (d < 1) {
            // Push along the ellipse normal direction.
            const push = (1 - d) * 1.6 * alpha;
            n.vx = (n.vx ?? 0) + (nx / d) * push * rx * 0.06;
            n.vy = (n.vy ?? 0) + (ny / d) * push * ry * 0.06;
          }
        }
      };
      fg.d3Force("centerHole", holeForce);
      // Strong elastic bounds so nothing flies out of the visible canvas.
      const boundsForce = (alpha: number) => {
        const padX = 50;
        const padY = 50;
        const maxX = size.w / 2 - padX;
        const maxY = size.h / 2 - padY;
        for (const n of graph.nodes as any[]) {
          if (n.fx != null || n.fy != null) continue;
          const x = n.x ?? 0, y = n.y ?? 0;
          if (Math.abs(x) > maxX) {
            n.vx = (n.vx ?? 0) - (x - Math.sign(x) * maxX) * 0.28 * alpha;
          }
          if (Math.abs(y) > maxY) {
            n.vy = (n.vy ?? 0) - (y - Math.sign(y) * maxY) * 0.28 * alpha;
          }
        }
      };
      fg.d3Force("bounds", boundsForce);
      const linkF = fg.d3Force("link");
      if (linkF) {
        linkF.distance((l: any) => (l.rel === "belongs_to" ? 20 : 48));
        linkF.strength((l: any) => (l.rel === "belongs_to" ? 0.95 : 0.35));
      }
      fg.d3ReheatSimulation();
    } catch {/* noop */}
  }, [ForceGraph, geom.rx, geom.ry, graph.nodes, size.w, size.h]);


  // Expose imperative focusNodes(ids): pan/zoom to the centroid of the given nodes.
  useEffect(() => {
    if (!apiRef) return;
    apiRef.current = {
      focusNodes: (ids: string[], biasX = 0) => {
        const fg = fgRef.current;
        if (!fg || !ids.length) return;
        const set = new Set(ids);
        const targets = (graph.nodes as any[]).filter(
          (n) => set.has(n.id) && n.layer !== "proposition" && typeof n.x === "number",
        );
        if (!targets.length) return;
        let sx = 0, sy = 0;
        for (const n of targets) { sx += n.x; sy += n.y; }
        const cx = sx / targets.length;
        const cy = sy / targets.length;
        try {
          const z = fg.zoom?.() ?? 1;
          // Shift the view left by biasX/zoom so the focused nodes land to the RIGHT of
          // the centre, clear of the pleading card (which we move left at the same time).
          fg.centerAt?.(cx - biasX / z, cy, 600);
          fg.zoom?.(Math.max(1, z), 600);
        } catch {/* noop */}
      },
    };
    return () => { if (apiRef) apiRef.current = null; };
  }, [apiRef, graph.nodes]);

  const neighbours = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const e of data.edges) {
      if (!map.has(e.source)) map.set(e.source, new Set());
      if (!map.has(e.target)) map.set(e.target, new Set());
      map.get(e.source)!.add(e.target);
      map.get(e.target)!.add(e.source);
    }
    return map;
  }, [data.edges]);

  const focusId = hoveredId ?? selectedId;
  const focused = useMemo(() => {
    if (!focusId) return null;
    const set = new Set<string>([focusId]);
    neighbours.get(focusId)?.forEach((id) => set.add(id));
    return set;
  }, [focusId, neighbours]);

  useEffect(() => {
    if (!fgRef.current || !reducedMotion) return;
    try {
      fgRef.current.d3ReheatSimulation();
      for (let i = 0; i < 200; i++) fgRef.current.tickFrame?.();
    } catch {/* noop */}
  }, [reducedMotion, ForceGraph, mode]);

  if (!ForceGraph) {
    return (
      <div
        ref={wrapRef}
        className="relative h-full w-full overflow-hidden rounded-sm border"
        style={{ borderColor: COLORS.hair, background: COLORS.panel }}
      >
        <div className="absolute inset-0 grid place-items-center font-mono text-[10px] uppercase tracking-[0.25em] text-ink-dim">
          initialising graph...
        </div>
      </div>
    );
  }

  const onWheel: React.WheelEventHandler<HTMLDivElement> = (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;
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
        cooldownTicks={reducedMotion ? 0 : 200}
        warmupTicks={reducedMotion ? 200 : 60}
        d3VelocityDecay={0.4}
        linkDirectionalParticles={(l: any) => (focused && isLinkFocused(l, focused) ? 2 : 0)}
        linkDirectionalParticleSpeed={0.006}
        nodeRelSize={5}
        enableNodeDrag={true}
        enableZoomInteraction={false}
        enablePanInteraction={true}
        onRenderFramePre={(ctx: CanvasRenderingContext2D) => {
          if (hideHub) return;
          const radius = geom.hole;
          ctx.save();
          ctx.beginPath();
          ctx.arc(0, 0, radius - 6, 0, Math.PI * 2);
          ctx.fillStyle = withAlpha(COLORS.panel2 ?? COLORS.panel, 0.55);
          ctx.fill();
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 4]);
          ctx.strokeStyle = withAlpha(COLORS.ink, 0.18);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.font = '600 10px "IBM Plex Mono", monospace';
          ctx.fillStyle = withAlpha(COLORS.ink, 0.55);
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText("PLEADING", 0, -radius + 16);
          ctx.restore();
        }}
        onNodeHover={(n: any) => onHover(n ? n.id : null)}
        onNodeClick={(n: any, ev: MouseEvent) => {
          onSelect(n?.id ?? null);
          onSelectEdge(null);
          if (n && onNodeClickScreen && wrapRef.current) {
            const rect = wrapRef.current.getBoundingClientRect();
            onNodeClickScreen(n.id, ev.clientX - rect.left, ev.clientY - rect.top);
          }
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
          l.rel === "belongs_to" ? 0 : l.rel === "asserts" ? 2.5 : 4.5
        }
        linkDirectionalArrowRelPos={0.88}
        linkDirectionalParticleWidth={2}
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, scale: number) => {
          const isHover = hoveredId === node.id;
          const isSelected = selectedId === node.id;
          const dimmed = focused && !focused.has(node.id);
          const color = nodeColor(node);
          const r =
            node.layer === "proposition" ? 11
              : node.layer === "document" ? 8 + Math.min(4, (node.weight ?? 1) * 0.5)
              : 5 + Math.min(3, (node.weight ?? 1) * 0.6);

          if (isHover || isSelected) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 8, 0, 2 * Math.PI);
            ctx.fillStyle = withAlpha(color, 0.18);
            ctx.fill();
          }

          ctx.beginPath();
          if (node.layer === "document") {
            ctx.rect(node.x - r, node.y - r, r * 2, r * 2);
          } else {
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          }
          ctx.fillStyle = dimmed ? withAlpha(color, 0.18) : color;
          ctx.fill();

          if (node.load_bearing) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 2.5, 0, 2 * Math.PI);
            ctx.lineWidth = 1.4;
            ctx.strokeStyle = withAlpha(COLORS.brass, dimmed ? 0.35 : 1);
            ctx.stroke();
          }

          if (isSelected) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 5, 0, 2 * Math.PI);
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = COLORS.accent;
            ctx.stroke();
          }

          const showLabel =
            node.layer === "document" || isHover || isSelected || scale > 1.8;
          if (showLabel) {
            ctx.font = `${node.layer === "proposition" ? 600 : 500} ${
              node.layer === "proposition" ? 11 : 10
            }px "IBM Plex Sans", sans-serif`;
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            const text =
              node.layer === "proposition"
                ? ""
                : node.layer === "document"
                  ? `${node.label} · ${truncate(node.title, 28)}`
                  : truncate(node.fulltext ?? node.label, 36);
            if (!text) return;
            const pad = 4;
            const x = node.x + r + 6;
            const y = node.y;
            const w = ctx.measureText(text).width;
            ctx.fillStyle = withAlpha(COLORS.panel, dimmed ? 0.6 : 0.92);
            ctx.fillRect(x - pad, y - 8, w + pad * 2, 16);
            ctx.fillStyle = dimmed ? COLORS.inkDim : COLORS.ink;
            ctx.fillText(text, x, y);
          }
        }}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const r = node.layer === "proposition" ? 14 : node.layer === "document" ? 11 : 9;
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
      <ZoomControls
        onZoomIn={() => { const fg = fgRef.current; if (!fg?.zoom) return; fg.zoom(Math.min(8, fg.zoom() * 1.35), 220); }}
        onZoomOut={() => { const fg = fgRef.current; if (!fg?.zoom) return; fg.zoom(Math.max(0.2, fg.zoom() / 1.35), 220); }}
        onFit={() => { const fg = fgRef.current; if (!fg?.zoomToFit) return; fg.zoomToFit(400, 80); }}
        onRecenter={() => { const fg = fgRef.current; if (!fg?.centerAt) return; fg.centerAt(0, 0, 400); fg.zoom(1, 400); }}
      />
    </div>
  );
}

function ZoomControls({
  onZoomIn, onZoomOut, onFit, onRecenter,
}: { onZoomIn: () => void; onZoomOut: () => void; onFit: () => void; onRecenter: () => void }) {
  const btn = "h-8 w-8 grid place-items-center font-mono text-[13px] leading-none hover:bg-black/5 transition";
  return (
    <div
      className="absolute left-3 top-3 flex flex-col rounded-sm border overflow-hidden"
      style={{ borderColor: COLORS.hair, background: withAlpha(COLORS.panel, 0.95), color: COLORS.ink }}
    >
      <button onClick={onZoomIn} className={btn} title="Zoom in">＋</button>
      <button onClick={onZoomOut} className={btn + " border-t"} style={{ borderColor: COLORS.hair }} title="Zoom out">−</button>
      <button onClick={onFit} className={btn + " border-t text-[10px]"} style={{ borderColor: COLORS.hair }} title="Fit graph">⤢</button>
      <button onClick={onRecenter} className={btn + " border-t text-[11px]"} style={{ borderColor: COLORS.hair }} title="Recenter">⊕</button>
    </div>
  );
}


function isLinkFocused(l: any, focused: Set<string>): boolean {
  return focused.has(srcId(l.source)) && focused.has(srcId(l.target));
}

function withAlpha(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

function truncate(s: string, n: number): string {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "..." : s;
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
  const links: Array<[string, string]> = [
    ["supports", COLORS.accepted],
    ["contradicts", COLORS.rejected],
    ["supersedes / attacks", COLORS.orange],
    ["caps / legal bar", COLORS.legal],
    ["asserts", COLORS.accent],
  ];
  const verdicts: Array<[string, string]> = [
    ["supported", COLORS.accepted],
    ["contradicted", COLORS.rejected],
    ["legal overlay", COLORS.legal],
    ["not addressed", COLORS.absence],
  ];
  const div = <div className="my-1.5 h-px" style={{ background: COLORS.hair }} />;

  return (
    <div
      className="pointer-events-none absolute bottom-3 left-3 rounded-sm border px-3 py-2 text-[10px] uppercase tracking-widest text-ink-dim"
      style={{
        borderColor: COLORS.hair,
        background: withAlpha(COLORS.panel, 0.94),
        fontFamily: '"IBM Plex Mono", monospace',
      }}
    >
      <div className="mb-1 text-ink">Legend</div>

      <div className="flex items-center gap-2 leading-5">
        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: COLORS.inkDim }} />
        <span>claim</span>
      </div>
      <div className="flex items-center gap-2 leading-5">
        <span className="inline-block h-2.5 w-2.5" style={{ background: COLORS.accent }} />
        <span>document</span>
      </div>
      <div className="flex items-center gap-2 leading-5">
        <span className="inline-block h-2.5 w-2.5 rounded-full border" style={{ borderColor: COLORS.brass, borderWidth: 1.5 }} />
        <span>load-bearing</span>
      </div>

      {div}
      {verdicts.map(([k, c]) => (
        <div key={k} className="flex items-center gap-2 leading-5">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: c }} />
          <span>{k}</span>
        </div>
      ))}

      {div}
      {links.map(([k, c]) => (
        <div key={k} className="flex items-center gap-2 leading-5">
          <span className="inline-block h-[2px] w-5" style={{ background: c }} />
          <span>{k}</span>
        </div>
      ))}
    </div>
  );
}
