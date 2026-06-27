import { useMemo } from "react";
import type { AppData, ClaimNode, PropositionNode } from "@/lib/pleading";
import { COLORS, verdictColor } from "@/lib/pleading";

interface Props {
  data: AppData;
  selectedId: string | null;
  hoveredId: string | null;
  highlightedIds: Set<string>;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  mode?: "stress" | "coherence";
}

// The pleading is presented as a legal document. Each proposition becomes a
// numbered paragraph; the pleading-side claim (verbatim quote) is highlighted
// inline by its verdict colour. Clicking a paragraph selects the proposition.
export default function PleadingView({
  data,
  selectedId,
  hoveredId,
  highlightedIds,
  onSelect,
  onHover,
}: Props) {
  const propositions = useMemo(
    () => data.nodes.filter((n) => n.layer === "proposition") as PropositionNode[],
    [data],
  );

  const pleadingClaimByProp = useMemo(() => {
    const m = new Map<string, ClaimNode>();
    for (const n of data.nodes) {
      if (n.layer === "claim" && n.polarity === "pleading" && n.prop) {
        m.set(n.prop, n as ClaimNode);
      }
    }
    return m;
  }, [data]);

  return (
    <section
      className="flex h-full flex-col overflow-hidden rounded-sm border"
      style={{ borderColor: COLORS.hair, background: COLORS.panel }}
    >
      <header className="border-b px-7 py-5" style={{ borderColor: COLORS.hair }}>
        <div className="rule-label">Statement of Case</div>
        <h2 className="mt-1 font-display text-[24px] italic leading-tight">
          Particulars of Claim
        </h2>
        <p className="mt-2 text-[13.5px] leading-relaxed text-ink-dim">
          The pleading, as filed. Highlighted spans are the verbatim allegations;
          their colour reflects whether the bundle{" "}
          <span style={{ color: COLORS.accepted }}>supports</span>,{" "}
          <span style={{ color: COLORS.rejected }}>contradicts</span>, or{" "}
          <span style={{ color: COLORS.absence }}>does not address</span> them.
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-8 py-7 lg:px-10 lg:py-9">
        <div className="mx-auto max-w-[68ch]">
          <div className="mb-7 border-b pb-5 text-center" style={{ borderColor: COLORS.hair }}>
            <div className="font-mono text-[11px] uppercase tracking-[0.28em] text-ink-dim">
              In the {data.meta.court}
            </div>
            <div className="mt-1.5 font-mono text-[11px] tracking-widest text-ink-dim">
              Claim No. {data.meta.claim_no}
            </div>
            <div className="mt-3.5 font-display text-[18px] italic">{data.meta.case}</div>
            <div className="mt-3 font-display text-[15px] uppercase tracking-[0.18em]">
              Particulars of Claim
            </div>
          </div>

          <ol className="space-y-6">
            {propositions.map((p, i) => {
              const pc = pleadingClaimByProp.get(p.label);
              const verdictC = verdictColor(p.verdict);
              const isSelected = selectedId === p.id || selectedId === pc?.id;
              const isHover = hoveredId === p.id || hoveredId === pc?.id;
              const isLinked = highlightedIds.has(p.id) || (pc && highlightedIds.has(pc.id));
              const dim =
                (selectedId || hoveredId) && !isSelected && !isHover && !isLinked;

              // The pleading text: use the verbatim claim quote when available;
              // otherwise fall back to the proposition text.
              const body = pc?.quote ?? p.text;

              return (
                <li
                  key={p.id}
                  className="group relative"
                  onMouseEnter={() => onHover(p.id)}
                  onMouseLeave={() => onHover(null)}
                  style={{ opacity: dim ? 0.35 : 1, transition: "opacity 150ms" }}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(p.id)}
                    className="block w-full cursor-pointer text-left focus:outline-none"
                  >
                    <div className="flex items-baseline gap-3">
                      <span
                        className="shrink-0 font-mono text-[11px] uppercase tracking-[0.2em] text-ink-dim"
                        style={{ minWidth: "2.6rem" }}
                      >
                        {i + 1}.
                      </span>
                      <div className="flex-1">
                        <p className="font-display text-[15px] leading-[1.7] text-ink">
                          <mark
                            className="rounded-[2px] px-1 py-[1px]"
                            style={{
                              background: isSelected
                                ? `${verdictC}38`
                                : isLinked
                                  ? `${verdictC}28`
                                  : `${verdictC}18`,
                              boxShadow: isSelected
                                ? `inset 0 -2px 0 0 ${verdictC}`
                                : `inset 0 -1px 0 0 ${verdictC}80`,
                              color: COLORS.ink,
                            }}
                          >
                            {body}
                          </mark>
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          <span
                            className="font-mono text-[10px] uppercase tracking-[0.18em]"
                            style={{ color: COLORS.inkDim }}
                          >
                            {p.label}
                            {pc?.anchor && (
                              <span className="ml-2 text-ink-dim/70">¶ {pc.anchor}</span>
                            )}
                          </span>
                          <span
                            className="verdict-pill"
                            style={{
                              borderColor: verdictC,
                              color: verdictC,
                              background: `${verdictC}12`,
                            }}
                          >
                            {p.verdict.replace("_", " ")}
                          </span>
                          {p.overlay && p.overlay !== "NONE" && (
                            <span
                              className="inline-flex items-center rounded-sm border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest"
                              style={{ borderColor: COLORS.legal, color: COLORS.legal }}
                            >
                              Legal · {p.overlay.replace(/_/g, " ").toLowerCase()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ol>

          <div
            className="mt-10 border-t pt-4 text-right font-display text-[12px] italic text-ink-dim"
            style={{ borderColor: COLORS.hair }}
          >
            Served this day on behalf of the Claimant.
          </div>
        </div>
      </div>
    </section>
  );
}
