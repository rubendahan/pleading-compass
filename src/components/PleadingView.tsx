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
      <header className="border-b px-5 py-3" style={{ borderColor: COLORS.hair }}>
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <div className="rule-label">Statement of Case</div>
            <h2 className="mt-0.5 font-display text-[20px] italic leading-tight">
              Particulars of Claim
            </h2>
          </div>
          <div className="text-right font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim">
            <div>{data.meta.court}</div>
            <div className="mt-0.5">Claim {data.meta.claim_no}</div>
          </div>
        </div>
        <p className="mt-2 text-[12px] leading-snug text-ink-dim">
          Highlighted spans are verbatim allegations; colour shows whether the bundle{" "}
          <span style={{ color: COLORS.accepted }}>supports</span>,{" "}
          <span style={{ color: COLORS.rejected }}>contradicts</span>, or{" "}
          <span style={{ color: COLORS.absence }}>does not address</span> them.
        </p>
      </header>

      <div id="pleading-scroll" className="flex-1 overflow-y-auto px-6 py-5">
        <div className="w-full">
          <div className="mb-4 text-center font-display text-[14px] italic text-ink">
            {data.meta.case}
          </div>

          <ol className="space-y-4">

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
                    <div className="flex items-baseline gap-3.5">
                      <span
                        className="shrink-0 font-mono text-[12px] uppercase tracking-[0.2em] text-ink-dim"
                        style={{ minWidth: "2.8rem" }}
                      >
                        {i + 1}.
                      </span>
                      <div className="flex-1">
                        <p className="font-display text-[17px] leading-[1.75] text-ink">
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
                        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
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
