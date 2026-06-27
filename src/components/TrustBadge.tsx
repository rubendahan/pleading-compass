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
