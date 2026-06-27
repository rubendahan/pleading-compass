import { useEffect, useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { COLORS } from "@/lib/pleading";
import demoCase from "@/lib/demo-case.json";

type Para = { n: number; text: string };
type Doc = { title: string; doc_type: string; party: string; paras: Para[] };
type Docs = Record<string, Doc>;

function parseAnchor(a: string) {
  const m = a.match(/^([0-9A-Za-z]+)¶(\d+)$/); // e.g. "08¶7"
  return m ? { doc: m[1], para: parseInt(m[2], 10) } : null;
}

/** A clickable source anchor (e.g. "08¶7"). Opens the source document at that
 *  paragraph, with the verbatim quote highlighted, so a lawyer can verify it fast. */
export function AnchorButton({
  anchor, quote, documents,
}: { anchor: string | null | undefined; quote?: string | null; documents?: Docs }) {
  const [open, setOpen] = useState(false);
  if (!anchor) return null;
  const parsed = parseAnchor(anchor);
  const docs: Docs = (documents ?? (demoCase as any).documents ?? {}) as Docs;
  const doc = parsed ? docs[parsed.doc] : undefined;

  return (
    <>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(true); }}
        className="inline-flex items-center gap-1.5 rounded border px-2 py-0.5 font-mono text-[11px] transition hover:bg-bg/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        style={{ borderColor: COLORS.hair, color: COLORS.brass }}
        title="Open the source document at this paragraph"
      >
        {anchor}
        <span aria-hidden style={{ color: COLORS.inkDim }}>verify</span>
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl" style={{ background: COLORS.panel, borderColor: COLORS.hair }}>
          <DialogHeader>
            <DialogTitle className="font-display text-[18px]">
              {doc ? doc.title : `Document ${parsed?.doc ?? ""}`}
            </DialogTitle>
          </DialogHeader>
          {doc ? (
            <Reader doc={doc} para={parsed?.para} quote={quote} />
          ) : (
            <p className="text-sm text-ink-dim">
              Full document text is not loaded for this case. Create a fresh demo case to read sources in context.
            </p>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

function Reader({ doc, para, quote }: { doc: Doc; para?: number; quote?: string | null }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const t = setTimeout(() => ref.current?.scrollIntoView({ block: "center" }), 60);
    return () => clearTimeout(t);
  }, [para]);

  return (
    <div className="max-h-[68vh] overflow-y-auto pr-1">
      <div className="mb-3 flex gap-2 font-mono text-[10px] uppercase tracking-widest text-ink-dim">
        <span className="rounded border px-2 py-0.5" style={{ borderColor: COLORS.hair }}>{doc.doc_type}</span>
        <span className="rounded border px-2 py-0.5" style={{ borderColor: COLORS.hair }}>{doc.party}</span>
      </div>
      <div className="space-y-1.5 text-[13px] leading-relaxed">
        {doc.paras.map((p) => {
          const hit = p.n === para;
          return (
            <div
              key={p.n}
              ref={hit ? ref : undefined}
              className="flex gap-3 rounded p-2"
              style={hit ? { background: `${COLORS.brass}14`, borderLeft: `2px solid ${COLORS.brass}` } : undefined}
            >
              <span className="shrink-0 pt-0.5 font-mono text-[10px] text-ink-dim">{p.n}</span>
              <span className="text-ink">{hit ? renderHighlighted(p.text, quote) : p.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function renderHighlighted(text: string, quote?: string | null) {
  if (!quote) return text;
  const i = text.indexOf(quote);
  if (i < 0) return text;
  return (
    <>
      {text.slice(0, i)}
      <mark style={{ background: `${COLORS.legal}33`, color: COLORS.ink, padding: "0 2px", borderRadius: 2 }}>
        {text.slice(i, i + quote.length)}
      </mark>
      {text.slice(i + quote.length)}
    </>
  );
}
