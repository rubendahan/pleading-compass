import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { analyzeBundle, createDemoCase } from "@/lib/firm.functions";
import { COLORS } from "@/lib/pleading";
import UploadBundle from "@/components/UploadBundle";
import AnalyzeProgress from "@/components/AnalyzeProgress";

export const Route = createFileRoute("/_authenticated/cases/new")({
  head: () => ({ meta: [{ title: "New case" }] }),
  component: NewCasePage,
});

type Phase = "upload" | "analyzing";

function NewCasePage() {
  const navigate = useNavigate();
  const seed = useServerFn(createDemoCase);
  const analyze = useServerFn(analyzeBundle);

  const [phase, setPhase] = useState<Phase>("upload");
  const [fileCount, setFileCount] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  // We kick the case creation off the moment analysis starts, then await it when
  // the staged animation finishes. The wait paces the navigation either way.
  const pending = useRef<Promise<{ id: string }> | null>(null);

  function handleAnalyze(files: File[]) {
    setErr(null);
    setFileCount(files.length);
    setPhase("analyzing");
    // If an engine is wired up (ENGINE_URL set server-side), analyzeBundle posts the
    // uploaded files to it and seeds a real case. With no engine it throws, and we
    // fall back to the demo seed — the current behaviour, unchanged.
    const descriptors = files.map((f) => ({ name: f.name, type: f.type, size: f.size }));
    pending.current = analyze({ data: { files: descriptors } }).catch(() => seed());
  }

  async function handleDone() {
    try {
      const result = await (pending.current ?? seed());
      navigate({ to: "/cases/$caseId", params: { caseId: result.id } });
    } catch (e: any) {
      setErr(e?.message ?? String(e));
      setPhase("upload");
      pending.current = null;
    }
  }

  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="border-b px-6 py-4" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
        <div className="mx-auto max-w-3xl">
          <Link to="/cases" className="font-mono text-[10px] uppercase tracking-[0.28em] text-ink-dim hover:text-ink">
            ← All cases
          </Link>
          <h1 className="mt-1.5 font-display text-[24px] leading-tight">New case</h1>
          <p className="mt-1 font-mono text-[11px] text-ink-dim">
            Upload the bundle. We read it, anchor every quote, and annotate the pleading.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10">
        {phase === "upload" ? (
          <>
            <UploadBundle onAnalyze={handleAnalyze} />
            {err && (
              <div
                className="mt-4 rounded-sm border px-3 py-2 font-mono text-[11px]"
                style={{ borderColor: COLORS.rejected, color: COLORS.rejected }}
              >
                {err}
              </div>
            )}
            <p className="mt-5 text-center font-mono text-[10px] leading-relaxed tracking-[0.04em] text-ink-dim">
              Demo build. Whatever you drop, this run loads the sample case
              (Meridian v TechFlow) so you can explore a fully analysed file.
            </p>
          </>
        ) : (
          <AnalyzeProgress fileCount={fileCount} onDone={handleDone} />
        )}
      </main>
    </div>
  );
}
