import { useMemo, useState } from "react";
import type { AppData } from "@/lib/pleading";
import { COLORS, tabLabel, anchorLabel } from "@/lib/pleading";
import { AnchorButton } from "./SourceReader";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  if (!y) return iso;
  return d ? `${parseInt(d, 10)} ${MONTHS[parseInt(m, 10) - 1]}` : `${MONTHS[parseInt(m, 10) - 1]}`;
}
const anchorOf = (tab: string, para: number | null | undefined) =>
  para != null ? `${tab}¶${para}` : tab;

/**
 * Dense, year-grouped chronology. Facts collapse by year (most recent open by
 * default) and stay one line each. Documents are a compact table.
 */
export default function Chronology({ data }: { data: AppData }) {
  const [tab, setTab] = useState<"facts" | "documents">("facts");
  const facts = data.chronology ?? [];
  const docs = (data.doc_index ?? []).slice().sort((a, b) => (a.date ?? "").localeCompare(b.date ?? ""));

  const grouped = useMemo(() => {
    const m = new Map<string, typeof facts>();
    for (const f of facts) {
      const y = (f.date ?? "").slice(0, 4) || "—";
      if (!m.has(y)) m.set(y, [] as any);
      (m.get(y) as any).push(f);
    }
    return Array.from(m.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [facts]);

  const lastYear = grouped.length ? grouped[grouped.length - 1][0] : null;
  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    lastYear ? { [lastYear]: true } : {},
  );

  return (
    <div className="h-full overflow-y-auto bg-bg">
      <div className="mx-auto max-w-[820px] px-4 py-6 sm:px-8">
        <div className="mb-4 flex items-center justify-between border-b pb-3" style={{ borderColor: COLORS.hair }}>
          <h2 className="font-display text-[22px]">Chronology</h2>
          <div className="inline-flex rounded-sm border p-0.5" style={{ borderColor: COLORS.hair, background: COLORS.panel2 }}>
            {(["facts", "documents"] as const).map((k) => (
              <button key={k} onClick={() => setTab(k)}
                className="rounded-sm px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em] transition"
                style={{ color: tab === k ? COLORS.panel : COLORS.ink, background: tab === k ? COLORS.ink : "transparent" }}>
                {k === "facts" ? `Facts · ${facts.length}` : `Docs · ${docs.length}`}
              </button>
            ))}
          </div>
        </div>

        {tab === "facts" ? (
          facts.length === 0 ? (
            <Empty label="No chronology of facts yet." />
          ) : (
            <div className="space-y-3">
              {grouped.map(([year, items]) => {
                const isOpen = !!open[year];
                return (
                  <div key={year} className="rounded-sm border" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
                    <button
                      onClick={() => setOpen((s) => ({ ...s, [year]: !s[year] }))}
                      className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-panel2"
                    >
                      <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink-dim">
                        {year} · <span className="text-ink">{items.length}</span>
                      </span>
                      <span className="font-mono text-[11px] text-ink-dim">{isOpen ? "−" : "+"}</span>
                    </button>
                    {isOpen && (
                      <ul className="divide-y" style={{ borderColor: COLORS.hair }}>
                        {items.map((f) => (
                          <li key={f.n} className="grid grid-cols-[64px_1fr_auto] items-baseline gap-3 px-3 py-2">
                            <span className="font-mono text-[10px] tracking-wide text-ink-dim">{fmtDate(f.date)}</span>
                            <p className="font-display text-[13.5px] leading-snug">{f.event}</p>
                            <span className="flex flex-wrap items-center justify-end gap-1">
                              {(f.evidence ?? []).slice(0, 2).map((e, i) => (
                                <AnchorButton key={i} anchor={anchorOf(e.tab, e.para)} label={anchorLabel(anchorOf(e.tab, e.para))}
                                  documents={data.documents} />
                              ))}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>
          )
        ) : docs.length === 0 ? (
          <Empty label="No document index yet." />
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
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.tab} className="border-t" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
                    <td className="whitespace-nowrap px-3 py-1.5 font-mono text-ink-dim">{tabLabel(d.tab)}</td>
                    <td className="px-3 py-1.5 font-display text-[13px]">{d.title}</td>
                    <td className="whitespace-nowrap px-3 py-1.5 font-mono text-ink-dim">{fmtDate(d.date)}</td>
                    <td className="px-3 py-1.5">
                      <span className="rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest"
                        style={{ color: COLORS.ink, background: COLORS.panel2 }}>{d.category}</span>
                    </td>
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
    <div className="grid place-items-center rounded-sm border py-12 text-[12px] text-ink-dim"
      style={{ borderColor: COLORS.hair }}>
      {label}
    </div>
  );
}
