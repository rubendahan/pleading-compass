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
  /** Click-to-source: open the in-site reader/PDF for the clicked node. */
  onOpenSource?: (id: string) => void;
  /** Imperative API ref: caller can pan/zoom to a set of node ids, with an optional
   * horizontal screen bias (px) so the nodes land to the right of a centre card. */
  apiRef?: React.MutableRefObject<{ focusNodes: (ids: string[], biasX?: number) => void } | null>;

}

// Labels are decluttered by zoom: anything that is not focused or a key corpus
// anchor stays hidden until the reader zooms past these thresholds.
const LABEL_ZOOM = 1.6;
const LABEL_ZOOM_PROP = 2.4;

interface LabelBox { x0: number; y0: number; x1: number; y1: number }

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
  onOpenSource,
  apiRef,
}: Props) {

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const fgRef = useRef<any>(null);
  // Rectangles already taken by labels this frame, so the sparse zoom-in labels
  // can be skipped when they would collide with text already on screen.
  const placedLabelsRef = useRef<LabelBox[]>([]);
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

  // Tune the d3-force layout. Charge/links shape the spread; the hole + bounds keep
  // nodes on-screen with a *position* correction (deadband + clamp) instead of the old
  // velocity injection, which jittered because it never settled. NB: this effect does
  // NOT reheat — reheating lives in a separate data/mode effect so a resize stays calm.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg?.d3Force) return;
    try {
      fg.d3Force("charge")?.strength(-120).distanceMax(220).theta(0.9);

      // Elliptical centre hole: nudge free nodes just outside the card, gently.
      const holeForce = (alpha: number) => {
        const rx = geom.rx + 18;
        const ry = geom.ry + 18;
        for (const n of graph.nodes as any[]) {
          if (n.layer === "proposition") continue;
          if (n.fx != null || n.fy != null) continue;
          const x = n.x ?? 0, y = n.y ?? 0;
          const nx = x / rx, ny = y / ry;
          const d = Math.sqrt(nx * nx + ny * ny) || 0.0001;
          const gap = 1 - d;
          if (gap > 0.02) {
            // Move a clamped fraction of the way to the ellipse boundary.
            const k = Math.min(0.25, gap) * alpha;
            const bx = (nx / d) * rx, by = (ny / d) * ry;
            n.x = x + (bx - x) * k;
            n.y = y + (by - y) * k;
          }
        }
      };
      fg.d3Force("centerHole", holeForce);

      // Soft elastic bounds: pull stragglers back toward the visible canvas.
      const boundsForce = (alpha: number) => {
        const maxX = size.w / 2 - 50;
        const maxY = size.h / 2 - 50;
        for (const n of graph.nodes as any[]) {
          if (n.fx != null || n.fy != null) continue;
          const x = n.x ?? 0, y = n.y ?? 0;
          if (Math.abs(x) > maxX + 4) {
            const target = Math.sign(x) * maxX;
            n.x = x + (target - x) * Math.min(0.3, alpha);
          }
          if (Math.abs(y) > maxY + 4) {
            const target = Math.sign(y) * maxY;
            n.y = y + (target - y) * Math.min(0.3, alpha);
          }
        }
      };
      fg.d3Force("bounds", boundsForce);

      const linkF = fg.d3Force("link");
      if (linkF) {
        linkF.distance((l: any) =>
          l.rel === "belongs_to" ? 18 : l.rel === "asserts" ? 40 : 60,
        );
        linkF.strength((l: any) =>
          l.rel === "belongs_to" ? 0.9 : l.rel === "asserts" ? 0.25 : 0.3,
        );
      }
    } catch {/* noop */}
  }, [ForceGraph, geom.rx, geom.ry, graph.nodes, size.w, size.h]);

  // Reheat only when the underlying data or mode changes — never on resize, so
  // dragging the panel divider or resizing the window does not relaunch the layout.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg?.d3ReheatSimulation) return;
    try { fg.d3ReheatSimulation(); } catch {/* noop */}
  }, [ForceGraph, data, mode]);


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

  // Connectivity drives importance: a heavily cited document or a high-weight /
  // load-bearing claim reads as a larger, always-labelled corpus anchor.
  const degree = useMemo(() => {
    const m = new Map<string, number>();
    for (const n of data.nodes) m.set(n.id, neighbours.get(n.id)?.size ?? 0);
    return m;
  }, [data.nodes, neighbours]);

  const keyLabelIds = useMemo(() => {
    const docDegs = data.nodes
      .filter((n) => n.layer === "document")
      .map((n) => degree.get(n.id) ?? 0)
      .sort((a, b) => b - a);
    // Keep the most-connected ~40% of documents permanently labelled.
    const docCut = docDegs.length
      ? docDegs[Math.min(docDegs.length - 1, Math.floor((docDegs.length - 1) * 0.4))]
      : 0;
    const set = new Set<string>();
    for (const n of data.nodes as any[]) {
      if (n.load_bearing) { set.add(n.id); continue; }
      if (n.layer === "document" && (degree.get(n.id) ?? 0) >= Math.max(3, docCut)) set.add(n.id);
      else if (n.layer === "claim" && (n.weight ?? 1) >= 4) set.add(n.id);
    }
    return set;
  }, [data.nodes, degree]);

  // Radius encodes importance; load-bearing keeps the gold ring drawn separately.
  const radiusFor = (node: any): number => {
    if (node.layer === "proposition") return 11;
    if (node.layer === "document") {
      const d = degree.get(node.id) ?? 0;
      return 7 + Math.min(6, d * 1.2);
    }
    const w = node.weight ?? 1;
    return 5 + Math.min(5, (w - 1) * 1.3) + (node.load_bearing ? 1.6 : 0);
  };

  const focusId = hoveredId ?? selectedId;
  // The focus set is the full 2-hop evidence cluster, not just immediate neighbours,
  // so focusing a claim keeps its whole cluster legible instead of greying it out.
  const focused = useMemo(() => {
    if (!focusId) return null;
    const set = new Set<string>([focusId]);
    const one = neighbours.get(focusId);
    one?.forEach((id) => {
      set.add(id);
      neighbours.get(id)?.forEach((j) => set.add(j));
    });
    return set;
  }, [focusId, neighbours]);

  // Decide whether a node shows its label, and whether that label has reserved
  // priority (it is drawn no matter what) or is a sparse zoom-in label (drawn
  // only if it does not collide with text already placed this frame).
  const wantsLabel = (node: any, scale: number): { show: boolean; priority: boolean } => {
    if (focused) {
      // Under focus only the focused neighbourhood speaks; the rest goes quiet.
      return focused.has(node.id)
        ? { show: true, priority: true }
        : { show: false, priority: false };
    }
    if (node.layer === "proposition") {
      return scale > LABEL_ZOOM_PROP ? { show: true, priority: false } : { show: false, priority: false };
    }
    if (keyLabelIds.has(node.id)) return { show: true, priority: true };
    return scale > LABEL_ZOOM ? { show: true, priority: false } : { show: false, priority: false };
  };

  // Measure a node's label box (sets the font as a side effect, so the caller
  // can immediately draw using the same metrics).
  const labelRect = (node: any, ctx: CanvasRenderingContext2D) => {
    setLabelFont(ctx, node);
    const text = labelTextFor(node);
    const r = radiusFor(node);
    const w = ctx.measureText(text).width;
    const pad = 4;
    const lx = node.x + r + 6;
    return { text, lx, x0: lx - pad, y0: node.y - 9, x1: lx + w + pad, y1: node.y + 9 };
  };

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
        warmupTicks={reducedMotion ? 200 : 20}
        d3VelocityDecay={0.3}
        d3AlphaDecay={0.0228}
        d3AlphaMin={0.001}
        linkDirectionalParticles={(l: any) => (focused && isLinkFocused(l, focused) ? 2 : 0)}
        linkDirectionalParticleSpeed={0.006}
        nodeRelSize={5}
        enableNodeDrag={true}
        enableZoomInteraction={false}
        enablePanInteraction={true}
        onRenderFramePre={(ctx: CanvasRenderingContext2D) => {
          // Labels are no longer drawn here — they live in a single top layer in
          // onRenderFramePost so later-painted nodes can't overpaint earlier labels.
          // This pass only paints the hub disc that sits *under* the nodes.
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
          // Click-to-source: a node click opens the in-site source/PDF reader.
          if (n && onOpenSource) onOpenSource(n.id);
          if (n && onNodeClickScreen && wrapRef.current) {
            const rect = wrapRef.current.getBoundingClientRect();
            onNodeClickScreen(n.id, ev.clientX - rect.left, ev.clientY - rect.top);
          }
        }}
        // Pin a node where it is dragged so it doesn't spring back (non-jumpy drag).
        onNodeDrag={(n: any) => { n.fx = n.x; n.fy = n.y; }}
        onNodeDragEnd={(n: any) => { n.fx = n.x; n.fy = n.y; }}
        onLinkClick={(l: any) => {
          onSelectEdge(l.raw ?? null);
          onSelect(null);
        }}
        onBackgroundClick={() => {
          onSelect(null);
          onSelectEdge(null);
        }}
        linkColor={(l: any) => {
          const c = edgeColor(l.rel);
          if (focused) {
            return isLinkFocused(l, focused)
              ? withAlpha(c, l.rel === "asserts" ? 0.7 : 0.9)
              : withAlpha(c, 0.2);
          }
          return withAlpha(c, l.rel === "asserts" ? 0.4 : 0.7);
        }}
        linkWidth={(l: any) => {
          const isFocus = focused && isLinkFocused(l, focused);
          if (l.raw?.hard) return isFocus ? 3 : 1.5;
          if (l.rel === "asserts") return isFocus ? 1.6 : 0.6;
          return isFocus ? 2.6 : 1.1;
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
          const inFocus = !focused || focused.has(node.id);
          const dimmed = !!focused && !focused.has(node.id);
          const color = nodeColor(node);
          const r = radiusFor(node);

          if (isHover || isSelected) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 9, 0, 2 * Math.PI);
            ctx.fillStyle = withAlpha(color, 0.16);
            ctx.fill();
          }

          ctx.beginPath();
          if (node.layer === "document") {
            ctx.rect(node.x - r, node.y - r, r * 2, r * 2);
          } else {
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          }
          // Soft de-emphasis: unrelated nodes recede but the focused cluster, and the
          // dimmed nodes themselves, stay legible (not greyed into illegibility).
          ctx.fillStyle = dimmed ? withAlpha(color, 0.3) : color;
          ctx.fill();

          // A crisp hairline on in-focus nodes makes the focused cluster read solid.
          if (focused && inFocus && !isSelected) {
            ctx.lineWidth = 1;
            ctx.strokeStyle = withAlpha(COLORS.ink, 0.25);
            ctx.stroke();
          }

          if (node.load_bearing) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 2.5, 0, 2 * Math.PI);
            ctx.lineWidth = 1.4;
            ctx.strokeStyle = withAlpha(COLORS.brass, dimmed ? 0.45 : 1);
            ctx.stroke();
          }

          if (isSelected) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 5, 0, 2 * Math.PI);
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = COLORS.accent;
            ctx.stroke();
          }
          // Labels are intentionally NOT drawn here — see onRenderFramePost.
        }}
        onRenderFramePost={(ctx: CanvasRenderingContext2D, globalScale: number) => {
          // All labels render in this single top layer, after every link and node,
          // so text is never overpainted. Priority labels (focused subgraph + key
          // corpus anchors) are reserved and drawn first; sparse zoom-in labels then
          // fill the gaps only where they don't collide with text already placed.
          const placed: LabelBox[] = [];

          const drawLabel = (node: any, rect: ReturnType<typeof labelRect>) => {
            const emphasised = hoveredId === node.id || selectedId === node.id;
            ctx.fillStyle = withAlpha(COLORS.panel, emphasised ? 0.96 : 0.9);
            ctx.fillRect(rect.x0, rect.y0, rect.x1 - rect.x0, rect.y1 - rect.y0);
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            ctx.fillStyle = emphasised ? COLORS.ink : withAlpha(COLORS.ink, 0.9);
            ctx.fillText(rect.text, rect.lx, node.y);
          };

          // Pass 1 — priority labels: always shown, reserve their boxes.
          for (const node of graph.nodes as any[]) {
            if (typeof node.x !== "number" || typeof node.y !== "number") continue;
            const { show, priority } = wantsLabel(node, globalScale);
            if (!show || !priority) continue;
            const rect = labelRect(node, ctx);
            if (!rect.text) continue;
            placed.push({ x0: rect.x0, y0: rect.y0, x1: rect.x1, y1: rect.y1 });
            drawLabel(node, rect);
          }
          placedLabelsRef.current = placed;

          // Pass 2 — sparse zoom-in labels: drawn only when collision-free.
          for (const node of graph.nodes as any[]) {
            if (typeof node.x !== "number" || typeof node.y !== "number") continue;
            const { show, priority } = wantsLabel(node, globalScale);
            if (!show || priority) continue;
            const rect = labelRect(node, ctx);
            if (!rect.text) continue;
            const box: LabelBox = { x0: rect.x0, y0: rect.y0, x1: rect.x1, y1: rect.y1 };
            let clash = false;
            for (const p of placed) { if (rectsOverlap(box, p)) { clash = true; break; } }
            if (clash) continue;
            placed.push(box);
            drawLabel(node, rect);
          }
        }}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          // Comfortable click target: always a little larger than what is drawn.
          const pad = node.layer === "document" ? 6 : 5;
          const r = Math.max(node.layer === "proposition" ? 15 : 12, radiusFor(node) + pad);
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

function rectsOverlap(a: LabelBox, b: LabelBox): boolean {
  return a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
}

function labelTextFor(node: any): string {
  if (node.layer === "proposition") return truncate(node.label ?? "", 22);
  if (node.layer === "document") return `${node.label} · ${truncate(node.title, 26)}`;
  return truncate(node.fulltext ?? node.label, 34);
}

function setLabelFont(ctx: CanvasRenderingContext2D, node: any): void {
  const isProp = node.layer === "proposition";
  ctx.font = `${isProp ? 600 : 500} ${isProp ? 11 : 10}px "IBM Plex Sans", sans-serif`;
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
      <div className="flex items-center gap-2 leading-5">
        <span className="inline-flex items-center gap-0.5">
          <span className="inline-block rounded-full" style={{ width: 5, height: 5, background: COLORS.inkDim }} />
          <span className="inline-block rounded-full" style={{ width: 9, height: 9, background: COLORS.inkDim }} />
        </span>
        <span>size = how load-bearing</span>
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
