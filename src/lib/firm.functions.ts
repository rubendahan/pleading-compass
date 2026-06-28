import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import type { Json } from "@/integrations/supabase/types";
import type { AppData } from "@/lib/pleading";
import demoCase from "./demo-case.json";
import euCase from "./eu-case.json";

// Bootstrap context: returns the user's firm, role, full name.
export const getMyContext = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabase, userId } = context;
    const { data: profile } = await supabase
      .from("profiles")
      .select("id, firm_id, full_name, email")
      .eq("id", userId)
      .maybeSingle();
    const { data: roles } = await supabase
      .from("user_roles")
      .select("role, firm_id")
      .eq("user_id", userId);
    let firm: { id: string; name: string } | null = null;
    if (profile?.firm_id) {
      const { data } = await supabase
        .from("firms")
        .select("id, name")
        .eq("id", profile.firm_id)
        .maybeSingle();
      firm = data ?? null;
    }
    return {
      profile,
      firm,
      roles: roles ?? [],
      isAdmin: (roles ?? []).some((r) => r.role === "firm_admin"),
    };
  });

// Create a firm + grant admin role + seed a demo case. Called once after signup.
export const createFirmWithDemo = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: { firmName: string; fullName: string }) =>
    z.object({ firmName: z.string().trim().min(2).max(120), fullName: z.string().trim().min(2).max(120) }).parse(input),
  )
  .handler(async ({ data, context }) => {
    const { supabase, userId } = context;
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

    // Already in a firm? bail.
    const { data: existing } = await supabase
      .from("profiles")
      .select("firm_id")
      .eq("id", userId)
      .maybeSingle();
    if (existing?.firm_id) return { firmId: existing.firm_id, alreadyExisted: true };

    // 1) Create firm (admin client, no RLS)
    const { data: firm, error: firmErr } = await supabaseAdmin
      .from("firms")
      .insert({ name: data.firmName })
      .select("id")
      .single();
    if (firmErr || !firm) throw new Error(firmErr?.message || "firm insert failed");

    // 2) Update profile
    await supabaseAdmin
      .from("profiles")
      .update({ firm_id: firm.id, full_name: data.fullName })
      .eq("id", userId);

    // 3) Grant firm_admin role
    await supabaseAdmin
      .from("user_roles")
      .insert({ user_id: userId, role: "firm_admin", firm_id: firm.id });

    // 4) Seed demo case
    const m = (demoCase as any).meta ?? {};
    await supabaseAdmin.from("cases").insert({
      firm_id: firm.id,
      title: m.case ?? "Demo Case",
      claim_no: m.claim_no ?? null,
      court: m.court ?? null,
      data: demoCase,
      created_by: userId,
    });

    return { firmId: firm.id, alreadyExisted: false };
  });

// Invite a lawyer to the firm (admin only). Creates user via admin API and grants lawyer role.
export const inviteLawyer = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: { email: string; password: string; fullName: string }) =>
    z.object({
      email: z.string().trim().email().max(255),
      password: z.string().min(8).max(128),
      fullName: z.string().trim().min(2).max(120),
    }).parse(input),
  )
  .handler(async ({ data, context }) => {
    const { supabase, userId } = context;
    const { data: prof } = await supabase
      .from("profiles")
      .select("firm_id")
      .eq("id", userId)
      .maybeSingle();
    if (!prof?.firm_id) throw new Error("No firm");
    const { data: isAdmin } = await supabase
      .from("user_roles")
      .select("role")
      .eq("user_id", userId)
      .eq("role", "firm_admin")
      .eq("firm_id", prof.firm_id)
      .maybeSingle();
    if (!isAdmin) throw new Error("Forbidden: firm admin only");

    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: created, error: createErr } = await supabaseAdmin.auth.admin.createUser({
      email: data.email,
      password: data.password,
      email_confirm: true,
      user_metadata: { full_name: data.fullName },
    });
    if (createErr || !created.user) throw new Error(createErr?.message || "user creation failed");

    const newId = created.user.id;
    await supabaseAdmin
      .from("profiles")
      .upsert({ id: newId, email: data.email, full_name: data.fullName, firm_id: prof.firm_id });
    await supabaseAdmin
      .from("user_roles")
      .insert({ user_id: newId, role: "lawyer", firm_id: prof.firm_id });

    return { userId: newId };
  });

// List cases for current firm.
export const listCases = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabase } = context;
    const { data, error } = await supabase
      .from("cases")
      .select("id, title, claim_no, court, updated_at")
      .order("updated_at", { ascending: false });
    if (error) throw new Error(error.message);
    return data ?? [];
  });

export const getCase = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: { id: string }) => z.object({ id: z.string().uuid() }).parse(input))
  .handler(async ({ data, context }) => {
    const { supabase } = context;
    const { data: row, error } = await supabase
      .from("cases")
      .select("id, title, claim_no, court, data, updated_at")
      .eq("id", data.id)
      .maybeSingle();
    if (error) throw new Error(error.message);
    if (!row) throw new Error("Case not found");
    return row;
  });

// Persist a full AppData JSON back to the case row. Used by the annotated
// pleading editor: the lawyer edits a pleaded paragraph, we write the whole
// analysis document back to "cases.data" for that id. Auth + supabase usage
// mirror getCase; RLS scopes the write to the caller's firm.
export const updateCase = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: { id: string; data: AppData }) =>
    z.object({ id: z.string().uuid(), data: z.custom<AppData>() }).parse(input),
  )
  .handler(async ({ data, context }) => {
    const { supabase } = context;
    const { data: row, error } = await supabase
      .from("cases")
      .update({ data: data.data as unknown as Json })
      .eq("id", data.id)
      .select("id, title, claim_no, court, data, updated_at")
      .maybeSingle();
    if (error) throw new Error(error.message);
    if (!row) throw new Error("Case not found");
    return row;
  });

// ---- Engine seam ----------------------------------------------------------
// The analysis engine is a separate service. When ENGINE_URL is set we POST the
// pleading + bundle (re-analysis) or the uploaded files (fresh analysis) to
// `${ENGINE_URL}/analyze` and expect a full AppData object back. When it is not
// set, these throw a typed EngineNotConfigured so the UI degrades gracefully.

/** Thrown when no engine is wired up. The client treats any failure as "fall back
 *  to the existing note", so this is mainly for server-side clarity/logging. */
export class EngineNotConfigured extends Error {
  constructor() {
    super("Re-analysis runs on the engine. Connect the backend to enable.");
    this.name = "EngineNotConfigured";
  }
}

const APP_DATA_KEYS = ["meta", "stats", "nodes", "edges", "clusters"] as const;

/** Validate that the engine returned something shaped like AppData. */
function assertAppData(x: any): asserts x is AppData {
  if (!x || typeof x !== "object") throw new Error("Engine returned a non-object payload");
  for (const k of APP_DATA_KEYS) {
    if (!(k in x)) throw new Error(`Engine returned malformed AppData (missing "${k}")`);
  }
}

async function callEngine(payload: unknown): Promise<AppData> {
  const ENGINE_URL = process.env.ENGINE_URL;
  if (!ENGINE_URL) throw new EngineNotConfigured();
  const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/analyze`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Engine error ${res.status} ${res.statusText}`);
  const appData = await res.json();
  assertAppData(appData);
  return appData;
}

// Re-run the analysis for an existing case after the pleading was edited. Mirrors
// updateCase: validates input, persists the returned AppData to cases.data, RLS
// scopes the write to the caller's firm.
export const reanalyzeCase = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: { id: string; pleading: unknown; bundle: unknown }) =>
    z.object({ id: z.string().uuid(), pleading: z.any(), bundle: z.any() }).parse(input),
  )
  .handler(async ({ data, context }) => {
    const appData = await callEngine({ pleading: data.pleading, bundle: data.bundle });
    const { supabase } = context;
    const { data: row, error } = await supabase
      .from("cases")
      .update({ data: appData as unknown as Json })
      .eq("id", data.id)
      .select("id, title, claim_no, court, data, updated_at")
      .maybeSingle();
    if (error) throw new Error(error.message);
    if (!row) throw new Error("Case not found");
    return row;
  });

// Fresh analysis from an uploaded bundle. Posts the file descriptors to the engine
// and seeds a new case from the AppData it returns (mirrors createDemoCase's insert).
export const analyzeBundle = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: { files: Array<{ name: string; type: string; size: number }> }) =>
    z.object({
      files: z.array(z.object({ name: z.string(), type: z.string(), size: z.number() })),
    }).parse(input),
  )
  .handler(async ({ data, context }) => {
    const appData = await callEngine({ files: data.files });
    const { supabase, userId } = context;
    const { data: prof } = await supabase
      .from("profiles").select("firm_id").eq("id", userId).maybeSingle();
    if (!prof?.firm_id) throw new Error("No firm");
    const m = (appData as any).meta ?? {};
    const { data: row, error } = await supabase
      .from("cases")
      .insert({
        firm_id: prof.firm_id,
        title: m.case ?? "Analysed Case",
        claim_no: m.claim_no ?? null,
        court: m.court ?? null,
        data: appData as unknown as Json,
        created_by: userId,
      })
      .select("id")
      .single();
    if (error) throw new Error(error.message);
    return row;
  });

export const createDemoCase = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabase, userId } = context;
    const { data: prof } = await supabase
      .from("profiles")
      .select("firm_id")
      .eq("id", userId)
      .maybeSingle();
    if (!prof?.firm_id) throw new Error("No firm");
    const m = (demoCase as any).meta ?? {};
    // Reuse the existing case of the same title instead of piling up duplicates, but
    // refresh its analysis to the latest bundled JSON so a redeploy of the demo data
    // propagates to the seeded row on the next click (no need to delete + recreate).
    const { data: existing } = await supabase
      .from("cases").select("id").eq("firm_id", prof.firm_id).eq("title", m.case ?? "Demo Case").limit(1).maybeSingle();
    if (existing?.id) {
      await supabase
        .from("cases")
        .update({ data: demoCase, claim_no: m.claim_no ?? null, court: m.court ?? null })
        .eq("id", existing.id);
      return existing;
    }
    const { data, error } = await supabase
      .from("cases")
      .insert({
        firm_id: prof.firm_id,
        title: m.case ?? "Demo Case",
        claim_no: m.claim_no ?? null,
        court: m.court ?? null,
        data: demoCase,
        created_by: userId,
      })
      .select("id")
      .single();
    if (error) throw new Error(error.message);
    return data;
  });

// A second, harder demo case grounded in real EU law (Brightmarket v Cobalt).
export const createEuCase = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabase, userId } = context;
    const { data: prof } = await supabase
      .from("profiles").select("firm_id").eq("id", userId).maybeSingle();
    if (!prof?.firm_id) throw new Error("No firm");
    const m = (euCase as any).meta ?? {};
    const { data: existing } = await supabase
      .from("cases").select("id").eq("firm_id", prof.firm_id).eq("title", m.case ?? "EU Case").limit(1).maybeSingle();
    if (existing?.id) {
      await supabase
        .from("cases")
        .update({ data: euCase, claim_no: m.claim_no ?? null, court: m.court ?? null })
        .eq("id", existing.id);
      return existing;
    }
    const { data, error } = await supabase
      .from("cases")
      .insert({
        firm_id: prof.firm_id,
        title: m.case ?? "EU Case",
        claim_no: m.claim_no ?? null,
        court: m.court ?? null,
        data: euCase,
        created_by: userId,
      })
      .select("id").single();
    if (error) throw new Error(error.message);
    return data;
  });

// Delete a case (RLS scopes it to the user's firm).
export const deleteCase = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: { id: string }) => z.object({ id: z.string().uuid() }).parse(input))
  .handler(async ({ data, context }) => {
    const { supabase } = context;
    const { error } = await supabase.from("cases").delete().eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const listFirmMembers = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabase } = context;
    const { data: members } = await supabase
      .from("profiles")
      .select("id, full_name, email");
    const { data: roles } = await supabase
      .from("user_roles")
      .select("user_id, role");
    const roleByUser = new Map<string, string[]>();
    (roles ?? []).forEach((r) => {
      const arr = roleByUser.get(r.user_id) ?? [];
      arr.push(r.role);
      roleByUser.set(r.user_id, arr);
    });
    return (members ?? []).map((m) => ({ ...m, roles: roleByUser.get(m.id) ?? [] }));
  });

// Demo-only: idempotently ensure a fixed demo admin account exists, with a
// firm and a seeded case. Returns credentials the client can then use to
// sign in. PUBLIC ENDPOINT - intentionally exposes a known demo password.
export const DEMO_ADMIN_EMAIL = "demo-admin@coherence.app";
export const DEMO_ADMIN_PASSWORD = "DemoAdmin!2026";

export const ensureDemoAdmin = createServerFn({ method: "POST" }).handler(async () => {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

  // 1) Find existing user via listUsers (no direct getByEmail in the admin API).
  let userId: string | null = null;
  const { data: list } = await supabaseAdmin.auth.admin.listUsers({ page: 1, perPage: 200 });
  const existing = list?.users?.find((u) => u.email?.toLowerCase() === DEMO_ADMIN_EMAIL);
  if (existing) {
    userId = existing.id;
  } else {
    const { data: created, error } = await supabaseAdmin.auth.admin.createUser({
      email: DEMO_ADMIN_EMAIL,
      password: DEMO_ADMIN_PASSWORD,
      email_confirm: true,
      user_metadata: { full_name: "Demo Admin" },
    });
    if (error || !created.user) throw new Error(error?.message || "demo user creation failed");
    userId = created.user.id;
  }

  // 2) Ensure profile exists.
  const { data: prof } = await supabaseAdmin
    .from("profiles")
    .select("id, firm_id")
    .eq("id", userId)
    .maybeSingle();
  if (!prof) {
    await supabaseAdmin
      .from("profiles")
      .insert({ id: userId, email: DEMO_ADMIN_EMAIL, full_name: "Demo Admin" });
  }

  // 3) Ensure firm + admin role + seeded case.
  let firmId = prof?.firm_id ?? null;
  if (!firmId) {
    const { data: firm, error: fErr } = await supabaseAdmin
      .from("firms")
      .insert({ name: "Demo Cabinet" })
      .select("id")
      .single();
    if (fErr || !firm) throw new Error(fErr?.message || "firm insert failed");
    firmId = firm.id;
    await supabaseAdmin.from("profiles").update({ firm_id: firmId }).eq("id", userId);
    await supabaseAdmin
      .from("user_roles")
      .insert({ user_id: userId, role: "firm_admin", firm_id: firmId });
    const m = (demoCase as any).meta ?? {};
    await supabaseAdmin.from("cases").insert({
      firm_id: firmId,
      title: m.case ?? "Demo Case",
      claim_no: m.claim_no ?? null,
      court: m.court ?? null,
      data: demoCase,
      created_by: userId,
    });
  }

  return { email: DEMO_ADMIN_EMAIL, password: DEMO_ADMIN_PASSWORD };
});
