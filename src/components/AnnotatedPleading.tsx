import { useMemo } from "react";
import type { AppData, DataNode } from "@/lib/pleading";
import { COLORS, verdictColor, anchorLabel, srcId } from "@/lib/pleading";
import { AnchorButton } from "./SourceReader";
import { TrustBadge } from "./TrustBadge";

/**
 * The hero view: the Particulars of Claim rendered as a legal document, each pleaded
 * paragraph annotated in the margin the way counsel marks up a pleading —
 * "Contradicted by Evidence: Tab 4 · ¶9" with a one-click verify to the real source.
 */
interface Props {
  data: AppData;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onHover: (id: string | null) => void;
}

type Controlling = { rel: string; src: DataNode & any; anchor: string | null; quote: string | null };

const VERDICT_PHRASE: Record<string, string> = {
  SUPPORTED: "Supported by evidence",
  CONTRADICTED: "Contradicted by evidence",
  NOT_ADDRESSED: "Not addressed",
  UNVERIFIED: "Unverified",
};

const REL_RANK: Record<string, number> = {
  contradicts: 4, supersedes: 4, legal_bar: 3, caps: 3, qualifies: 2, attacks: 2, supports: 3,
};

function controllingEvidence(pleadingClaimId: string, data: AppData): Controlling | null {
  let best: (Controlling & { rank: number }) | null = null;
  for (const e of data.edges) {
    if (e.kind !== "coherence") continue;
    if (srcId(e.target) !== pleadingClaimId) continue;
    const src: any = data.nodes.find((n) => n.id === srcId(e.source));
    if (!src || src.layer !== "claim" || src.polarity === "pleading") continue;
    const rank = (REL_RANK[e.rel] ?? 1) * 100 + (src.weight ?? 0);
    if (!best || rank > best.rank) {
      best = { rel: e.rel, src, anchor: src.anchor ?? null, quote: src.quote ?? null, rank };
    }
  }
  return best;
}

export default function AnnotatedPleading({ data, selectedId, onSelect, onHover }: Props) {
  const annotations = useMemo(() => {
    // anchor "02¶n" -> the pleaded allegations sitting at that paragraph
    const byPara = new Map<number, Array<{ prop: any; pc: any; ctrl: Controlling | null }>>();
    for (const n of data.nodes as any[]) {
      if (n.layer !== "claim" || n.polarity !== "pleading" || !n.anchor) continue;
      const [doc, para] = String(n.anchor).split("¶");
      if (doc !== "02") continue;
      const prop = data.nodes.find((p) => p.id === `prop:${n.prop}`);
      if (!prop) continue;
      const k = parseInt(para, 10);
      if (!byPara.has(k)) byPara.set(k, []);
      byPara.get(k)!.push({ prop, pc: n, ctrl: controllingEvidence(n.id, data) });
    }
    return byPara;
  }, [data]);

  const particulars = data.documents?.["02"];
  const meta = data.meta;

  return (
    <div className="h-full overflow-y-auto bg-bg">
      <div className="mx-auto max-w-[1180px] px-4 py-8 sm:px-8">
        {/* Document head */}
        <div className="mb-7 border-b pb-5 text-center" style={{ borderColor: COLORS.hair }}>
          <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-ink-dim">
            {meta.court}
          </div>
          <div className="mt-1 font-mono text-[10px] tracking-wide text-ink-dim">
            Claim {meta.claim_no}
          </div>
          <h2 className="mt-4 font-display text-[26px] leading-tight">Particulars of Claim</h2>
          <div className="mt-1.5 font-display italic text-[14px] text-ink-dim">{meta.case}</div>
        </div>

        {particulars ? (
          <ol className="space-y-1">
            {particulars.paras.map((p) => {
              const anns = annotations.get(p.n) ?? [];
              const active = anns.some(
                (a) => selectedId === a.prop.id || selectedId === a.pc.id,
              );
              const clickable = anns.length > 0;
              return (
                <li
                  key={p.n}
                  className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_330px]"
                >
                  {/* Pleaded paragraph */}
                  <div
                    onClick={clickable ? () => onSelect(anns[0].prop.id) : undefined}
                    onMouseEnter={clickable ? () => onHover(anns[0].pc.id) : undefined}
                    onMouseLeave={clickable ? () => onHover(null) : undefined}
                    className={`flex gap-3 rounded-sm px-3 py-2 transition ${
                      clickable ? "cursor-pointer" : ""
                    }`}
                    style={{
                      background: active ? COLORS.panel2 : "transparent",
                      boxShadow: active ? `inset 2px 0 0 ${COLORS.ink}` : undefined,
                    }}
                  >
                    <span className="shrink-0 pt-0.5 font-mono text-[11px] text-ink-dim">{p.n}</span>
                    <p
                      className="font-display text-[15px] leading-[1.7]"
                      style={{ color: clickable ? COLORS.ink : COLORS.inkDim }}
                    >
                      {p.text}
                    </p>
                  </div>

                  {/* Margin annotations (counsel-style) */}
                  <div className="space-y-2 lg:pt-1">
                    {anns.map((a) => (
                      <MarginNote key={a.prop.id} prop={a.prop} ctrl={a.ctrl} data={data}
                        active={active} onSelect={() => onSelect(a.prop.id)} />
                    ))}
                  </div>
                </li>
              );
            })}
          </ol>
        ) : (
          <PropositionFallback data={data} annotations={annotations} selectedId={selectedId} onSelect={onSelect} />
        )}
      </div>
    </div>
  );
}

function MarginNote({
  prop, ctrl, data, active, onSelect,
}: { prop: any; ctrl: Controlling | null; data: AppData; active: boolean; onSelect: () => void }) {
  const color = verdictColor(prop.verdict);
  const phrase = VERDICT_PHRASE[prop.verdict] ?? prop.verdict;
  const overlay = prop.overlay && prop.overlay !== "NONE" ? prop.overlay : null;

  return (
    <div
      onClick={onSelect}
      className="cursor-pointer rounded-sm border p-2.5 transition hover:shadow-sm"
      style={{
        borderColor: active ? color : COLORS.hair,
        background: COLORS.panel,
        borderLeft: `3px solid ${color}`,
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color }}>
          {prop.label} · {phrase}
        </span>
        <TrustBadge source={prop.source} />
      </div>

      {ctrl && (
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-ink-dim">
          <span>{anchorLabel(ctrl.anchor)}</span>
          <AnchorButton anchor={ctrl.anchor} quote={ctrl.quote} documents={data.documents} />
        </div>
      )}
      {!ctrl && prop.verdict === "NOT_ADDRESSED" && (
        <div className="mt-1 text-[11px] italic text-ink-dim">No supporting evidence in the bundle.</div>
      )}

      {overlay && (
        <div className="mt-1.5">
          <span
            className="inline-block rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest"
            style={{ color: COLORS.legal, background: `${COLORS.legal}14` }}
          >
            legal · {overlay.replace(/_/g, " ").toLowerCase()}
          </span>
        </div>
      )}
    </div>
  );
}

/** When a backend sends no document bodies, fall back to listing the pleaded allegations. */
function PropositionFallback({
  data, annotations, selectedId, onSelect,
}: { data: AppData; annotations: Map<number, any[]>; selectedId: string | null; onSelect: (id: string) => void }) {
  const props = data.nodes.filter((n) => n.layer === "proposition");
  const ctrlFor = (propId: string) => {
    for (const list of annotations.values())
      for (const a of list) if (a.prop.id === `prop:${propId}` || a.prop.id === propId) return a.ctrl;
    return null;
  };
  return (
    <ol className="space-y-3">
      {props.map((p: any) => (
        <li key={p.id} className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_330px]">
          <div className="flex gap-3 rounded-sm px-3 py-2">
            <span className="shrink-0 pt-0.5 font-mono text-[11px] text-ink-dim">{p.label}</span>
            <p className="font-display text-[15px] leading-[1.7]">{p.text}</p>
          </div>
          <div className="lg:pt-1">
            <MarginNote prop={p} ctrl={ctrlFor(p.label)} data={data} active={selectedId === p.id}
              onSelect={() => onSelect(p.id)} />
          </div>
        </li>
      ))}
    </ol>
  );
}
