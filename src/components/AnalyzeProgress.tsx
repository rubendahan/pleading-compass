import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Circle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { COLORS } from "@/lib/pleading";

/**
 * The staged "parsing" experience. Honest about what a real pipeline does:
 * read the bundle, identify documents, locate verbatim quotes, check coherence,
 * build the chronology, annotate the pleading. Each step ticks with a short
 * delay so the wait feels like work, not a spinner. When the last step lands we
 * call onDone, which the route uses to navigate into the prepared case.
 */
export interface AnalyzeProgressProps {
  fileCount?: number;
  onDone?: () => void;
}

interface Step {
  label: string;
  detail: string;
  /** Dwell time for this step, in ms. */
  ms: number;
}

const STEPS: Step[] = [
  { label: "Reading bundle", detail: "Opening every tab and splitting pages.", ms: 700 },
  { label: "Identifying documents", detail: "Naming pleadings, statements and exhibits.", ms: 850 },
  { label: "Locating verbatim quotes", detail: "Anchoring each assertion to its paragraph.", ms: 950 },
  { label: "Checking coherence", detail: "Cross-reading the bundle against the pleading.", ms: 1000 },
  { label: "Building chronology", detail: "Ordering the facts by date and source.", ms: 800 },
  { label: "Annotating pleading", detail: "Marking what is supported, missing or contradicted.", ms: 750 },
];

export default function AnalyzeProgress({ fileCount, onDone }: AnalyzeProgressProps) {
  // `step` = number of completed steps. The step at index `step` is in progress.
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    let acc = 0;
    STEPS.forEach((s, i) => {
      acc += s.ms;
      timers.push(setTimeout(() => setStep(i + 1), acc));
    });
    timers.push(setTimeout(() => onDone?.(), acc + 600));
    return () => timers.forEach(clearTimeout);
    // Run the timeline exactly once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const total = STEPS.length;
  const done = step >= total;
  // Nudge the bar partway through the active step so it never looks stalled.
  const value = Math.min(100, ((step + (done ? 0 : 0.5)) / total) * 100);

  return (
    <div className="rounded-sm border bg-panel" style={{ borderColor: COLORS.hair }}>
      <div className="border-b px-5 py-4 sm:px-7" style={{ borderColor: COLORS.hair }}>
        <div className="flex items-center justify-between gap-3">
          <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-ink-dim">
            {done ? "Analysis complete" : "Analysing bundle"}
          </div>
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-dim">
            {Math.min(step + (done ? 0 : 1), total)} / {total}
          </div>
        </div>
        <h2 className="mt-1.5 font-display text-[20px] leading-tight text-ink">
          {done ? "Your case is ready" : "Reading the binder cover to cover"}
        </h2>
        <p className="mt-1 font-mono text-[11px] text-ink-dim">
          {typeof fileCount === "number" && fileCount > 0
            ? `${fileCount} ${fileCount === 1 ? "document" : "documents"} in the bundle`
            : "Preparing the case for review"}
        </p>
        <div className="mt-4">
          <Progress value={value} className="h-2" />
        </div>
      </div>

      <ul className="px-5 py-2 sm:px-7">
        {STEPS.map((s, i) => {
          const state = i < step ? "done" : i === step && !done ? "active" : "pending";
          return (
            <li
              key={s.label}
              className="flex items-start gap-3 py-2.5 transition-opacity"
              style={{ opacity: state === "pending" ? 0.45 : 1 }}
            >
              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center">
                {state === "done" ? (
                  <CheckCircle2 className="h-5 w-5" strokeWidth={1.6} style={{ color: COLORS.accepted }} />
                ) : state === "active" ? (
                  <Loader2 className="h-5 w-5 animate-spin" strokeWidth={1.8} style={{ color: COLORS.brass }} />
                ) : (
                  <Circle className="h-4 w-4" strokeWidth={1.4} style={{ color: COLORS.inkDim }} />
                )}
              </span>
              <div className="min-w-0">
                <div
                  className="text-[14px] leading-tight"
                  style={{
                    color: state === "active" ? COLORS.ink : COLORS.ink,
                    fontWeight: state === "active" ? 600 : 400,
                  }}
                >
                  {s.label}
                </div>
                <div className="mt-0.5 font-mono text-[11px] text-ink-dim">{s.detail}</div>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="border-t px-5 py-3 sm:px-7" style={{ borderColor: COLORS.hair }}>
        <p className="font-mono text-[10px] leading-relaxed tracking-[0.04em] text-ink-dim">
          Demo run. This prepares the sample case (Meridian v TechFlow). No files are uploaded.
        </p>
      </div>
    </div>
  );
}
