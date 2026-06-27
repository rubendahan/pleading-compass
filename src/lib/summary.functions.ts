import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

const Input = z.object({
  caseId: z.string().uuid(),
  nodeId: z.string().min(1),
});

const SYSTEM = `You are a senior litigation associate writing a forensic, neutral, one-paragraph (max 90 words) note for the lead lawyer.
Write from the perspective of a pleading-vs-evidence coherence review.
For a pleaded ALLEGATION: state what the bundle does or does not establish, the strongest contradiction or absence, and the practical implication (caps damages, defeats causation, etc.).
For an evidentiary CLAIM: explain what it proves or undermines, its weight, and any load-bearing/single-source fragility.
For a DOCUMENT: summarise the role it plays in the bundle and what it tends to prove or disprove overall.
No hedging fluff, no markdown, no bullet points, no bold. Plain prose. End with one short next-step sentence prefixed with "Next: ".`;

export const summariseNode = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d: unknown) => Input.parse(d))
  .handler(async ({ data, context }) => {
    const key = process.env.LOVABLE_API_KEY;
    if (!key) throw new Error("LOVABLE_API_KEY missing on server");

    // Load case (RLS-scoped).
    const { data: row, error } = await context.supabase
      .from("cases")
      .select("data, title, claim_no, court")
      .eq("id", data.caseId)
      .maybeSingle();
    if (error) throw new Error(error.message);
    if (!row?.data) throw new Error("Case not found");

    const app = row.data as any;
    const node = (app.nodes ?? []).find((n: any) => n.id === data.nodeId);
    if (!node) throw new Error("Node not found in case");

    // Gather minimal context: incoming + outgoing edges and their counterpart node labels.
    const edges = (app.edges ?? []).filter(
      (e: any) => e.source === data.nodeId || e.target === data.nodeId,
    );
    const nodeMap = new Map<string, any>((app.nodes ?? []).map((n: any) => [n.id, n]));
    const relLines = edges.slice(0, 24).map((e: any) => {
      const isOut = e.source === data.nodeId;
      const other = nodeMap.get(isOut ? e.target : e.source);
      const otherLabel = other
        ? `${other.label}${other.layer === "claim" || other.layer === "proposition" ? ` - ${(other.fulltext ?? other.text ?? "").slice(0, 140)}` : other.title ? ` - ${other.title}` : ""}`
        : (isOut ? e.target : e.source);
      return `- ${e.rel}${e.hard ? " (hard)" : ""}${e.own_goal ? " [OWN GOAL]" : ""} ${isOut ? "→" : "←"} ${otherLabel}${e.explanation ? ` :: ${e.explanation}` : ""}`;
    });

    const header =
      node.layer === "proposition"
        ? `ALLEGATION ${node.label} - verdict ${node.verdict}, readiness ${node.readiness}/100, overlay ${node.overlay}\nText: ${node.text}`
        : node.layer === "claim"
          ? `CLAIM ${node.label} - verdict ${node.verdict}, polarity ${node.polarity}, source ${node.source_type}, weight ${node.weight}${node.load_bearing ? ", LOAD-BEARING" : ""}${node.single_source ? ", SINGLE-SOURCE" : ""}\nText: ${node.fulltext}\nQuote: ${node.quote ?? "n/a"}\nAnchor: ${node.anchor ?? "n/a"}`
          : `DOCUMENT ${node.label} - ${node.title} (${node.doc_type}, party: ${node.party})`;

    const userMsg = [
      `Case: ${row.title} · ${row.claim_no ?? ""} · ${row.court ?? ""}`,
      "",
      header,
      "",
      "Relations in bundle:",
      relLines.length ? relLines.join("\n") : "(none)",
    ].join("\n");

    const res = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "Lovable-API-Key": key,
      },
      body: JSON.stringify({
        model: "google/gemini-3-flash-preview",
        messages: [
          { role: "system", content: SYSTEM },
          { role: "user", content: userMsg },
        ],
      }),
    });

    if (res.status === 429) throw new Error("Rate limited. Please retry in a moment.");
    if (res.status === 402) throw new Error("AI credits exhausted on this workspace.");
    if (!res.ok) {
      const t = await res.text().catch(() => "");
      throw new Error(`AI gateway error ${res.status}: ${t.slice(0, 200)}`);
    }
    const json: any = await res.json();
    const text: string =
      json?.choices?.[0]?.message?.content ??
      json?.choices?.[0]?.delta?.content ??
      "";
    return { summary: text.trim() };
  });
