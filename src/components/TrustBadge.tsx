import { COLORS } from "@/lib/pleading";

/**
 * Separates what the lawyer can trust from what they must check.
 * `source: "ai"` (or "model") -> the item is an LLM inference -> "AI · verify".
 * Anything else (counsel-verified / deterministic) -> "from source".
 */
export function TrustBadge({ source, className = "" }: { source?: string | null; className?: string }) {
  const ai = source === "ai" || source === "model";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest ${className}`}
      style={ai
        ? { color: COLORS.legal, background: `${COLORS.legal}14` }
        : { color: COLORS.accepted, background: `${COLORS.accepted}14` }}
      title={ai ? "AI-suggested — verify against the source" : "Read from the source / counsel-verified"}
    >
      {ai ? "~ AI · verify" : "✓ from source"}
    </span>
  );
}

/**
 * Makes absence visible. Wherever support is empty or flagged, this turns a silent
 * blank into a call-to-action ("AI · verify") — same visual language as the AI
 * variant of TrustBadge. Optionally clickable to jump straight to the source.
 */
export function VerifyChip({
  reason,
  onClick,
  className = "",
}: {
  reason?: string | null;
  onClick?: () => void;
  className?: string;
}) {
  const style = { color: COLORS.legal, background: `${COLORS.legal}14` } as const;
  const label = "~ AI · verify";
  const title = reason || "No grounded support yet — open the source to verify";
  if (onClick) {
    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest transition hover:brightness-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${className}`}
        style={style}
        title={title}
      >
        {label}
      </button>
    );
  }
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest ${className}`}
      style={style}
      title={title}
    >
      {label}
    </span>
  );
}
