import { useRef, useState } from "react";
import { UploadCloud, FileText, X, Plus, ArrowRight, Layers } from "lucide-react";
import { COLORS } from "@/lib/pleading";

/**
 * The onboarding dropzone. A lawyer drops the whole binder here: pleadings,
 * witness statements, exhibits, the trial bundle. Pure UI + local state, no
 * upload backend. When they press "Analyze bundle" we hand the FileList up.
 */
export interface UploadBundleProps {
  onAnalyze: (files: File[]) => void;
  busy?: boolean;
}

const ACCEPT = ".pdf,.doc,.docx,.txt,.rtf,.png,.jpg,.jpeg,.tiff,.eml,.msg,.csv,.xlsx";

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 KB";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  const v = bytes / Math.pow(1024, i);
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
}

function fileKind(file: File): string {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (["pdf"].includes(ext)) return "PDF";
  if (["doc", "docx", "rtf"].includes(ext)) return "DOC";
  if (["png", "jpg", "jpeg", "tiff", "gif", "webp"].includes(ext)) return "IMAGE";
  if (["eml", "msg"].includes(ext)) return "EMAIL";
  if (["csv", "xlsx", "xls"].includes(ext)) return "SHEET";
  if (["txt"].includes(ext)) return "TEXT";
  return ext ? ext.toUpperCase() : "FILE";
}

const KIND_COLOR: Record<string, string> = {
  PDF: COLORS.rejected,
  DOC: COLORS.brass,
  IMAGE: COLORS.legal,
  EMAIL: COLORS.accepted,
  SHEET: COLORS.accepted,
  TEXT: COLORS.inkDim,
};

function fileKey(f: File): string {
  return `${f.name}::${f.size}::${f.lastModified}`;
}

export default function UploadBundle({ onAnalyze, busy = false }: UploadBundleProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  function addFiles(incoming: FileList | File[] | null) {
    if (!incoming) return;
    const next = Array.from(incoming);
    setFiles((prev) => {
      const seen = new Set(prev.map(fileKey));
      const merged = [...prev];
      for (const f of next) {
        if (!seen.has(fileKey(f))) {
          seen.add(fileKey(f));
          merged.push(f);
        }
      }
      return merged;
    });
  }

  function removeAt(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  function openPicker() {
    inputRef.current?.click();
  }

  const totalBytes = files.reduce((s, f) => s + f.size, 0);
  const ready = files.length > 0 && !busy;

  return (
    <div className="rounded-sm border bg-panel" style={{ borderColor: COLORS.hair }}>
      {/* Dropzone */}
      <div className="p-5 sm:p-7">
        <div
          role="button"
          tabIndex={0}
          aria-label="Drop bundle files here or browse"
          onClick={openPicker}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              openPicker();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            if (!dragging) setDragging(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setDragging(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            addFiles(e.dataTransfer?.files ?? null);
          }}
          className="group grid cursor-pointer place-items-center rounded-sm border-2 border-dashed px-6 py-12 text-center transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          style={{
            borderColor: dragging ? COLORS.brass : COLORS.hair,
            background: dragging ? COLORS.panel2 : "transparent",
          }}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <div
            className="mb-4 grid h-14 w-14 place-items-center rounded-full border transition-transform group-hover:scale-105"
            style={{
              borderColor: dragging ? COLORS.brass : COLORS.hair,
              background: COLORS.panel,
              color: dragging ? COLORS.brass : COLORS.ink,
            }}
          >
            <UploadCloud className="h-6 w-6" strokeWidth={1.5} />
          </div>
          <div className="font-display text-[18px] leading-tight text-ink">
            {dragging ? "Release to add the binder" : "Drop your bundle here"}
          </div>
          <p className="mt-1.5 max-w-md text-[13px] leading-relaxed text-ink-dim">
            Pleadings, witness statements, exhibits, the full trial bundle. Drop the whole
            folder at once, or click to browse.
          </p>
          <span
            className="mt-4 inline-flex items-center gap-1.5 rounded-sm border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-dim"
            style={{ borderColor: COLORS.hair, background: COLORS.panel }}
          >
            <Plus className="h-3 w-3" strokeWidth={2} />
            Browse files
          </span>
          <p className="mt-3 font-mono text-[9px] uppercase tracking-[0.2em] text-ink-dim">
            PDF · DOCX · images · email · nothing leaves your device
          </p>
        </div>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="border-t" style={{ borderColor: COLORS.hair }}>
          <div
            className="flex items-center justify-between px-5 py-2.5 sm:px-7"
            style={{ background: COLORS.panel2 }}
          >
            <span className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-ink-dim">
              <Layers className="h-3.5 w-3.5" strokeWidth={1.6} />
              {files.length} {files.length === 1 ? "document" : "documents"} · {formatBytes(totalBytes)}
            </span>
            <button
              type="button"
              onClick={() => setFiles([])}
              disabled={busy}
              className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-dim hover:text-ink disabled:opacity-40"
            >
              Clear all
            </button>
          </div>
          <ul className="max-h-64 divide-y overflow-y-auto" style={{ borderColor: COLORS.hair }}>
            {files.map((f, i) => {
              const kind = fileKind(f);
              const color = KIND_COLOR[kind] ?? COLORS.inkDim;
              return (
                <li
                  key={fileKey(f) + i}
                  className="flex items-center gap-3 px-5 py-2.5 hover:bg-panel2 sm:px-7"
                >
                  <FileText className="h-4 w-4 shrink-0" strokeWidth={1.5} style={{ color }} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] text-ink" title={f.name}>
                      {f.name}
                    </div>
                    <div className="mt-0.5 flex items-center gap-2">
                      <span
                        className="rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest"
                        style={{ color, background: `${color}14` }}
                      >
                        {kind}
                      </span>
                      <span className="font-mono text-[10px] text-ink-dim">{formatBytes(f.size)}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeAt(i)}
                    disabled={busy}
                    aria-label={`Remove ${f.name}`}
                    className="grid h-7 w-7 shrink-0 place-items-center rounded-sm text-ink-dim transition hover:bg-panel2 hover:text-ink disabled:opacity-40"
                  >
                    <X className="h-4 w-4" strokeWidth={1.6} />
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Action bar */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 border-t px-5 py-4 sm:px-7"
        style={{ borderColor: COLORS.hair }}
      >
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-dim">
          {files.length === 0 ? "Add the bundle to begin" : "Bundle ready to analyse"}
        </span>
        <button
          type="button"
          disabled={!ready}
          onClick={() => onAnalyze(files)}
          className="inline-flex items-center gap-2 rounded-sm px-4 py-2 font-mono text-[11px] uppercase tracking-[0.18em] transition disabled:cursor-not-allowed disabled:opacity-40"
          style={{ background: COLORS.ink, color: COLORS.panel }}
        >
          {busy ? "Working" : "Analyze bundle"}
          {!busy && <ArrowRight className="h-4 w-4" strokeWidth={2} />}
        </button>
      </div>
    </div>
  );
}
