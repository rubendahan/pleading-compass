import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import demoCase from "./demo-case.json";

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

  // 1) Find existing user via listUsers (no direct getByEmail in v2 admin).
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
