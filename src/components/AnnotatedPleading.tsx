import { useMemo, useState } from "react";
import { useParams } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import type { AppData, DataNode } from "@/lib/pleading";
import { COLORS, verdictColor, anchorLabel, srcId } from "@/lib/pleading";
import { updateCase, reanalyzeCase } from "@/lib/firm.functions";
import { AnchorButton } from "./SourceReader";
import { TrustBadge, VerifyChip } from "./TrustBadge";

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
  /** Open the in-site source reader for a node (margin notes wire this through). */
  onOpenSource?: (id: string) => void;
  /** Lift a fresh AppData up to the page after a successful engine re-analysis. */
  onReanalyzed?: (data: AppData) => void;
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

export default function AnnotatedPleading({ data, selectedId, onSelect, onHover, onOpenSource, onReanalyzed }: Props) {
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

  // ---- Edit-the-pleading state --------------------------------------------
  // caseId comes from the route, so we never need a new prop from the page.
  const params = useParams({ strict: false }) as { caseId?: string };
  const caseId = params.caseId ?? null;
  const persist = useServerFn(updateCase);
  const reanalyze = useServerFn(reanalyzeCase);

  const [editing, setEditing] = useState(false);
  // drafts: working textarea values while editing, keyed by paragraph number.
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  // committed: edits that have been persisted, so the read-only view keeps them.
  const [committed, setCommitted] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState(false);
  const [savedOnce, setSavedOnce] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [reanalyzeNote, setReanalyzeNote] = useState<string | null>(null);
  const [reanalyzing, setReanalyzing] = useState(false);

  // The text shown for a paragraph: latest committed edit, else the source.
  const paraText = (n: number, original: string) => committed[n] ?? original;

  function startEdit() {
    const seed: Record<number, string> = {};
    for (const p of particulars?.paras ?? []) seed[p.n] = committed[p.n] ?? p.text;
    setDrafts(seed);
    setSaveError(null);
    setReanalyzeNote(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setSaveError(null);
  }

  async function handleSave() {
    if (!caseId) {
      setSaveError("No case id in route; cannot save.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      // Deep-clone the analysis document and replace only the pleaded text in
      // the Particulars of Claim (documents["02"]). Verdicts/edges are untouched.
      const next: AppData = JSON.parse(JSON.stringify(data));
      const doc = next.documents?.["02"];
      if (doc) {
        doc.paras = doc.paras.map((p) => ({ ...p, text: drafts[p.n] ?? p.text }));
      }
      await persist({ data: { id: caseId, data: next } });
      setCommitted({ ...drafts });
      setSavedOnce(true);
      setEditing(false);
    } catch (e: any) {
      setSaveError(String(e?.message ?? e));
    } finally {
      setSaving(false);
    }
  }

  async function handleReanalyze() {
    setReanalyzeNote(null);
    if (!caseId) {
      setReanalyzeNote("Re-analysis runs on the engine. Connect the backend to enable.");
      return;
    }
    setReanalyzing(true);
    try {
      // Send the latest pleading (with committed edits) + the bundle to the engine.
      const next: AppData = JSON.parse(JSON.stringify(data));
      const pleading = next.documents?.["02"];
      if (pleading) {
        pleading.paras = pleading.paras.map((p) => ({ ...p, text: committed[p.n] ?? p.text }));
      }
      const row: any = await reanalyze({
        data: { id: caseId, pleading: pleading ?? null, bundle: next.documents ?? null },
      });
      // Lift the fresh AppData the engine returned up to the page.
      if (row?.data) onReanalyzed?.(row.data as AppData);
    } catch {
      // No engine configured (or it failed): fall back to the existing note, unchanged.
      setReanalyzeNote("Re-analysis runs on the engine. Connect the backend to enable.");
    } finally {
      setReanalyzing(false);
    }
  }

  const btnBase =
    "rounded-sm border px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest transition disabled:opacity-50";

  return (
    <div className="h-full overflow-y-auto bg-bg">
      <div className="mx-auto max-w-[1180px] px-4 py-8 sm:px-8">
        {/* Edit controls: counsel can amend a pleaded paragraph and re-run analysis. */}
        {particulars && (
          <div className="mb-3 flex flex-wrap items-center justify-end gap-2">
            {editing ? (
              <>
                <button
                  onClick={cancelEdit}
                  disabled={saving}
                  className={btnBase + " text-ink-dim hover:text-ink"}
                  style={{ borderColor: COLORS.hair, background: COLORS.panel }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className={btnBase}
                  style={{ borderColor: COLORS.ink, background: COLORS.ink, color: COLORS.panel }}
                >
                  {saving ? "Saving" : "Save"}
                </button>
              </>
            ) : (
              <>
                {savedOnce && (
                  <button
                    onClick={handleReanalyze}
                    disabled={reanalyzing}
                    className={btnBase + " hover:shadow-sm"}
                    style={{ borderColor: COLORS.legal, color: COLORS.legal, background: `${COLORS.legal}10` }}
                  >
                    {reanalyzing ? "Re-analyzing" : "Re-analyze"}
                  </button>
                )}
                <button
                  onClick={startEdit}
                  className={btnBase + " text-ink-dim hover:text-ink"}
                  style={{ borderColor: COLORS.hair, background: COLORS.panel }}
                >
                  Edit
                </button>
              </>
            )}
          </div>
        )}

        {saveError && (
          <div
            className="mb-3 rounded-sm border px-3 py-2 font-mono text-[11px]"
            style={{ borderColor: COLORS.rejected, color: COLORS.rejected, background: `${COLORS.rejected}10` }}
          >
            {saveError}
          </div>
        )}

        {reanalyzeNote && (
          <div
            className="mb-3 flex items-start gap-2 rounded-sm border px-3 py-2 text-[12px]"
            style={{ borderColor: COLORS.legal, background: `${COLORS.legal}0d`, color: COLORS.ink }}
          >
            <span
              className="mt-px font-mono text-[9px] uppercase tracking-widest"
              style={{ color: COLORS.legal }}
            >
              backend
            </span>
            <span className="text-ink-dim">{reanalyzeNote}</span>
          </div>
        )}

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
          {editing && (
            <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.22em]" style={{ color: COLORS.legal }}>
              Editing. Amend pleaded paragraphs, then Save.
            </div>
          )}
        </div>

        {particulars ? (
          <ol className="space-y-1">
            {particulars.paras.map((p) => {
              const anns = annotations.get(p.n) ?? [];
              const active = anns.some(
                (a) => selectedId === a.prop.id || selectedId === a.pc.id,
              );
              // While editing, the paragraph row is a text field, not a selector.
              const clickable = anns.length > 0 && !editing;
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
                    {editing ? (
                      <textarea
                        value={drafts[p.n] ?? p.text}
                        onChange={(e) =>
                          setDrafts((d) => ({ ...d, [p.n]: e.target.value }))
                        }
                        rows={Math.max(2, Math.ceil((drafts[p.n] ?? p.text).length / 88))}
                        className="w-full resize-y rounded-sm border px-2 py-1.5 font-display text-[15px] leading-[1.7] focus:outline-none"
                        style={{
                          color: COLORS.ink,
                          background: COLORS.panel,
                          borderColor: COLORS.hair,
                        }}
                      />
                    ) : (
                      <p
                        className="font-display text-[15px] leading-[1.7]"
                        style={{ color: anns.length > 0 ? COLORS.ink : COLORS.inkDim }}
                      >
                        {paraText(p.n, p.text)}
                      </p>
                    )}
                  </div>

                  {/* Margin annotations (counsel-style) */}
                  <div className="space-y-2 lg:pt-1">
                    {anns.map((a) => (
                      <MarginNote key={a.prop.id} prop={a.prop} ctrl={a.ctrl} data={data}
                        active={active} onSelect={() => onSelect(a.prop.id)}
                        onOpenSource={onOpenSource ? () => onOpenSource(a.prop.id) : undefined} />
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
  prop, ctrl, data, active, onSelect, onOpenSource,
}: { prop: any; ctrl: Controlling | null; data: AppData; active: boolean; onSelect: () => void; onOpenSource?: () => void }) {
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
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] italic text-ink-dim">
          <span>No supporting evidence in the bundle.</span>
          <VerifyChip
            reason="Pleaded on assertion — nothing in the bundle is anchored to this allegation"
            onClick={onOpenSource}
          />
        </div>
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
