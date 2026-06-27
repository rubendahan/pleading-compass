import { useState } from "react";
import type { AppData } from "@/lib/pleading";
import { COLORS, tabLabel, anchorLabel } from "@/lib/pleading";
import { AnchorButton } from "./SourceReader";
import { TrustBadge } from "./TrustBadge";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  if (!y) return iso;
  return d ? `${parseInt(d, 10)} ${MONTHS[parseInt(m, 10) - 1]} ${y}` : `${MONTHS[parseInt(m, 10) - 1]} ${y}`;
}
const anchorOf = (tab: string, para: number | null | undefined) =>
  para != null ? `${tab}¶${para}` : tab;

/**
 * The chronology the lawyer builds first: facts (dated, evidence-anchored) and the
 * document index (by Tab + date + category). Every row verifies to the real source.
 */
export default function Chronology({ data }: { data: AppData }) {
  const [tab, setTab] = useState<"facts" | "documents">("facts");
  const facts = data.chronology ?? [];
  const docs = (data.doc_index ?? []).slice().sort((a, b) => (a.date ?? "").localeCompare(b.date ?? ""));

  return (
    <div className="h-full overflow-y-auto bg-bg">
      <div className="mx-auto max-w-[900px] px-4 py-8 sm:px-8">
        <div className="mb-6 flex items-center justify-between border-b pb-4" style={{ borderColor: COLORS.hair }}>
          <h2 className="font-display text-[24px]">Chronology</h2>
          <div className="inline-flex rounded-sm border p-0.5" style={{ borderColor: COLORS.hair, background: COLORS.panel2 }}>
            {(["facts", "documents"] as const).map((k) => (
              <button key={k} onClick={() => setTab(k)}
                className="rounded-sm px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] transition"
                style={{ color: tab === k ? COLORS.panel : COLORS.ink, background: tab === k ? COLORS.ink : "transparent" }}>
                {k === "facts" ? "Facts" : "Documents"}
              </button>
            ))}
          </div>
        </div>

        {tab === "facts" ? (
          facts.length === 0 ? (
            <Empty label="No chronology of facts in this case yet." />
          ) : (
            <div className="ml-2 space-y-5 border-l pl-7" style={{ borderColor: COLORS.hair }}>
              {facts.map((f) => (
                <div key={f.n} className="relative">
                  <span className="absolute -left-[35px] top-1.5 h-2.5 w-2.5 rounded-full"
                    style={{ background: COLORS.ink, boxShadow: `0 0 0 4px ${COLORS.bg}` }} />
                  <div className="font-mono text-[11px] tracking-wide text-ink-dim">{fmtDate(f.date)}</div>
                  <div className="mt-1 rounded-sm border p-3" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
                    <p className="font-display text-[14px] leading-[1.65]">{f.event}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      {(f.evidence ?? []).map((e, i) => (
                        <AnchorButton key={i} anchor={anchorOf(e.tab, e.para)} label={anchorLabel(anchorOf(e.tab, e.para))}
                          documents={data.documents} />
                      ))}
                      <TrustBadge source={f.source} />
                    </div>
                    {f.remarks ? (
                      <div className="mt-2 text-[11px] italic text-ink-dim">{f.remarks}</div>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )
        ) : docs.length === 0 ? (
          <Empty label="No document index in this case yet." />
        ) : (
          <div className="overflow-hidden rounded-sm border" style={{ borderColor: COLORS.hair }}>
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="font-mono text-[9px] uppercase tracking-widest text-ink-dim"
                  style={{ background: COLORS.panel2 }}>
                  <th className="px-3 py-2">Tab</th>
                  <th className="px-3 py-2">Document</th>
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Party</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.tab} className="border-t" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
                    <td className="whitespace-nowrap px-3 py-2 font-mono text-ink-dim">{tabLabel(d.tab)}</td>
                    <td className="px-3 py-2 font-display text-[13px]">{d.title}</td>
                    <td className="whitespace-nowrap px-3 py-2 font-mono text-ink-dim">{fmtDate(d.date)}</td>
                    <td className="px-3 py-2">
                      <span className="rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest"
                        style={{ color: COLORS.ink, background: COLORS.panel2 }}>{d.category}</span>
                    </td>
                    <td className="px-3 py-2 text-ink-dim">{d.party}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return (
    <div className="grid place-items-center rounded-sm border py-16 text-[12px] text-ink-dim"
      style={{ borderColor: COLORS.hair }}>
      {label}
    </div>
  );
}
