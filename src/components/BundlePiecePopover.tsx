import { useEffect, useRef, useState } from "react";
import type { AppData, ClaimNode, DocumentNode, DataNode } from "@/lib/pleading";
import { COLORS, verdictColor } from "@/lib/pleading";

interface Props {
  data: AppData;
  nodeId: string;
  /** Initial anchor position in container pixels. */
  anchor: { x: number; y: number };
  /** Container box, to clamp & flip. */
  container: { w: number; h: number };
  onClose: () => void;
  onSelect: (id: string) => void;
  onOpenInspector: () => void;
}

const W = 360;
const MAX_H = 460;

/** A small draggable "bundle piece" card anchored near the clicked graph node.
 *  - Document node → show the doc header + its quote-grounded claims.
 *  - Claim node    → show the parent document header + this claim's quote.
 *  - Proposition   → show the pleaded paragraph.
 */
export default function BundlePiecePopover({
  data, nodeId, anchor, container, onClose, onSelect, onOpenInspector,
}: Props) {
  const node = data.nodes.find((n) => n.id === nodeId);
  const initial = useRef<{ x: number; y: number } | null>(null);

  // Position the card so it stays on-screen. Prefer to the right of the click.
  if (!initial.current) {
    let x = anchor.x + 18;
    let y = anchor.y - 40;
    if (x + W + 12 > container.w) x = Math.max(12, anchor.x - W - 18);
    if (y + 220 > container.h) y = Math.max(12, container.h - MAX_H - 12);
    if (y < 12) y = 12;
    initial.current = { x, y };
  }
  const [pos, setPos] = useState<{ x: number; y: number }>(initial.current);
  const dragRef = useRef<{ ox: number; oy: number; sx: number; sy: number } | null>(null);

  useEffect(() => {
    function onMove(e: PointerEvent) {
      const d = dragRef.current;
      if (!d) return;
      setPos({
        x: Math.max(8, Math.min(container.w - W - 8, d.ox + (e.clientX - d.sx))),
        y: Math.max(8, Math.min(container.h - 80, d.oy + (e.clientY - d.sy))),
      });
    }
    function onUp() { dragRef.current = null; }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [container.w, container.h]);

  if (!node) return null;

  // Resolve which doc + claim(s) to display.
  let doc: DocumentNode | null = null;
  let claim: ClaimNode | null = null;
  if (node.layer === "document") {
    doc = node as DocumentNode;
  } else if (node.layer === "claim") {
    claim = node as ClaimNode;
    const anchorDoc = claim.anchor?.split("¶")[0];
    doc = (data.nodes.find(
      (n) => n.layer === "document" && (n as DocumentNode).label === anchorDoc,
    ) as DocumentNode) ?? null;
  }

  const docClaims = doc
    ? data.nodes.filter(
        (n): n is ClaimNode =>
          n.layer === "claim" &&
          n.polarity !== "pleading" &&
          n.anchor?.split("¶")[0] === doc!.label,
      )
    : [];

  return (
    <div
      className="absolute z-30 select-none"
      style={{
        left: pos.x,
        top: pos.y,
        width: W,
        maxHeight: MAX_H,
      }}
    >
      <div
        className="flex h-full max-h-[460px] flex-col overflow-hidden rounded-sm border shadow-[0_24px_48px_-22px_rgba(20,17,13,0.55)]"
        style={{ borderColor: COLORS.hair, background: COLORS.panel }}
      >
        <header
          className="flex items-center justify-between gap-2 border-b px-3 py-2 cursor-grab active:cursor-grabbing"
          style={{ borderColor: COLORS.hair, background: COLORS.panel2 }}
          onPointerDown={(e) => {
            (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
            dragRef.current = { ox: pos.x, oy: pos.y, sx: e.clientX, sy: e.clientY };
          }}
        >
          <div className="flex items-center gap-2 truncate">
            <span className="text-ink-dim text-[10px] font-mono">⋮⋮</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim truncate">
              {node.layer === "proposition" ? "Pleaded allegation"
                : doc ? `Bundle · doc ${doc.label}`
                : "Bundle item"}
            </span>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={onOpenInspector}
              className="rounded-sm border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-ink-dim hover:text-ink"
              style={{ borderColor: COLORS.hair }}
              title="Open full analysis in side panel"
            >
              analysis
            </button>
            <button
              onClick={onClose}
              className="rounded-sm border px-1.5 py-0.5 font-mono text-[10px] text-ink-dim hover:text-ink"
              style={{ borderColor: COLORS.hair }}
              title="Close"
            >
              ✕
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-3.5 py-3 space-y-3">
          {node.layer === "proposition" && (
            <PropositionBody node={node as any} />
          )}
          {doc && (
            <DocBody doc={doc} highlightClaimId={claim?.id ?? null} claims={docClaims} onSelect={onSelect} />
          )}
          {node.layer === "claim" && !doc && (
            <ClaimBody claim={claim!} />
          )}
        </div>
      </div>
    </div>
  );
}

function PropositionBody({ node }: { node: DataNode & { layer: "proposition"; label: string; text: string; verdict: string } }) {
  const c = verdictColor(node.verdict);
  return (
    <>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim">
          {node.label}
        </span>
        <span
          className="verdict-pill"
          style={{ borderColor: c, color: c, background: `${c}1A` }}
        >
          {node.verdict.replace("_", " ")}
        </span>
      </div>
      <p className="font-display text-[14px] leading-relaxed text-ink">{node.text}</p>
    </>
  );
}

function DocBody({
  doc, highlightClaimId, claims, onSelect,
}: {
  doc: DocumentNode;
  highlightClaimId: string | null;
  claims: ClaimNode[];
  onSelect: (id: string) => void;
}) {
  return (
    <>
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-ink-dim">
            doc {doc.label} · {doc.doc_type}
          </span>
          <span
            className="rounded-sm border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest text-ink-dim"
            style={{ borderColor: COLORS.hair }}
          >
            {doc.party}
          </span>
        </div>
        <h3 className="mt-1 font-display text-[15px] leading-snug text-ink">{doc.title}</h3>
      </div>
      {claims.length === 0 ? (
        <p className="font-mono text-[10px] italic text-ink-dim">
          No quote-grounded claims drawn from this document.
        </p>
      ) : (
        <ul className="space-y-2">
          {claims.map((c) => {
            const isFocus = c.id === highlightClaimId;
            const col =
              c.polarity === "legal_overlay" ? COLORS.legal : verdictColor(c.verdict);
            return (
              <li key={c.id}>
                <button
                  onClick={() => onSelect(c.id)}
                  className="block w-full rounded-sm border p-2 text-left transition hover:bg-bg/40"
                  style={{
                    borderColor: isFocus ? col : COLORS.hair,
                    borderLeft: `3px solid ${col}`,
                    background: isFocus ? `${col}10` : "transparent",
                  }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-ink-dim truncate">
                      {c.issue}{c.anchor && <span className="ml-1 text-ink-dim/70">¶ {c.anchor}</span>}
                    </span>
                    <span
                      className="verdict-pill"
                      style={{ borderColor: col, color: col, background: `${col}14` }}
                    >
                      {c.polarity === "legal_overlay" ? "legal" : c.verdict}
                    </span>
                  </div>
                  <p className="mt-1 font-display text-[12.5px] leading-snug text-ink">{c.fulltext}</p>
                  {c.quote && (
                    <p className="mt-1 border-l-2 pl-2 font-display text-[11.5px] italic leading-snug text-ink-dim"
                       style={{ borderColor: COLORS.hair }}>
                      “{c.quote.length > 220 ? c.quote.slice(0, 219) + "…" : c.quote}”
                    </p>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

function ClaimBody({ claim }: { claim: ClaimNode }) {
  const c = claim.polarity === "legal_overlay" ? COLORS.legal : verdictColor(claim.verdict);
  return (
    <div className="rounded-sm border p-2"
         style={{ borderColor: COLORS.hair, borderLeft: `3px solid ${c}` }}>
      <div className="font-mono text-[9px] uppercase tracking-widest text-ink-dim">
        {claim.issue} {claim.anchor && <>· ¶ {claim.anchor}</>}
      </div>
      <p className="mt-1 font-display text-[13px] leading-snug text-ink">{claim.fulltext}</p>
      {claim.quote && (
        <p className="mt-1 border-l-2 pl-2 font-display text-[12px] italic leading-snug text-ink-dim"
           style={{ borderColor: COLORS.hair }}>
          “{claim.quote}”
        </p>
      )}
    </div>
  );
}
