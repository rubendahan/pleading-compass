import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { supabase } from "@/integrations/supabase/client";
import { getMyContext, listCases, createDemoCase, inviteLawyer, listFirmMembers } from "@/lib/firm.functions";
import { COLORS } from "@/lib/pleading";

export const Route = createFileRoute("/_authenticated/cases/")({
  component: CasesPage,
});

function CasesPage() {
  const navigate = useNavigate();
  const fetchCtx = useServerFn(getMyContext);
  const fetchCases = useServerFn(listCases);
  const seed = useServerFn(createDemoCase);
  const invite = useServerFn(inviteLawyer);
  const fetchMembers = useServerFn(listFirmMembers);

  const [ctx, setCtx] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [members, setMembers] = useState<any[]>([]);
  const [showInvite, setShowInvite] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    const [c, l, m] = await Promise.all([fetchCtx(), fetchCases(), fetchMembers()]);
    setCtx(c);
    setCases(l);
    setMembers(m);
  };

  useEffect(() => { load().catch((e) => setErr(String(e?.message ?? e))); }, []);

  async function handleSignOut() {
    await supabase.auth.signOut();
    navigate({ to: "/auth" });
  }

  if (!ctx) {
    return <div className="grid min-h-screen place-items-center bg-bg font-mono text-[11px] text-ink-dim">{err ?? "loading..."}</div>;
  }

  if (!ctx.firm) {
    return (
      <div className="grid min-h-screen place-items-center bg-bg p-6 text-center text-ink-dim">
        <div>
          <p className="mb-4">No cabinet attached to this account.</p>
          <Link to="/auth" className="font-mono text-[11px] uppercase tracking-widest underline">Open a cabinet</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="border-b px-6 py-4" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-ink-dim">Cabinet</div>
            <h1 className="font-display text-[22px] leading-tight">{ctx.firm.name}</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-[11px] text-ink-dim">
              {ctx.profile?.full_name} · {ctx.isAdmin ? "admin" : "lawyer"}
            </span>
            <button onClick={handleSignOut} className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim hover:text-ink">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <section className="mb-10">
          <div className="mb-3 flex items-end justify-between">
            <h2 className="font-display text-[18px]">Case files</h2>
            <div className="flex items-center gap-2">
              <Link
                to="/cases/new"
                className="rounded-sm px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em]"
                style={{ background: COLORS.ink, color: COLORS.panel }}
              >
                + New case
              </Link>
              <button
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try { const r = await seed(); navigate({ to: "/cases/$caseId", params: { caseId: r.id } }); }
                  finally { setBusy(false); }
                }}
                className="rounded-sm border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] disabled:opacity-50"
                style={{ borderColor: COLORS.hair }}
              >
                + New demo case
              </button>
            </div>
          </div>
          {cases.length === 0 ? (
            <p className="font-mono text-[12px] text-ink-dim">
              No cases yet. Start a <Link to="/cases/new" className="underline">new case</Link> or seed a demo case to explore the console.
            </p>
          ) : (
            <ul className="divide-y rounded-sm border bg-panel" style={{ borderColor: COLORS.hair }}>
              {cases.map((c) => (
                <li key={c.id}>
                  <Link
                    to="/cases/$caseId" params={{ caseId: c.id }}
                    className="block px-4 py-3 hover:bg-panel2"
                  >
                    <div className="font-display text-[15px]">{c.title}</div>
                    <div className="mt-0.5 font-mono text-[11px] text-ink-dim">
                      {c.claim_no ?? "n/a"} · {c.court ?? "n/a"} · updated {new Date(c.updated_at).toLocaleDateString()}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-end justify-between">
            <h2 className="font-display text-[18px]">Members</h2>
            {ctx.isAdmin && (
              <button
                onClick={() => setShowInvite((s) => !s)}
                className="rounded-sm border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em]"
                style={{ borderColor: COLORS.hair }}
              >
                {showInvite ? "Cancel" : "+ Invite lawyer"}
              </button>
            )}
          </div>
          {showInvite && (
            <InviteForm
              busy={busy}
              onSubmit={async (v) => {
                setBusy(true); setErr(null);
                try { await invite({ data: v }); setShowInvite(false); await load(); }
                catch (e: any) { setErr(e?.message ?? String(e)); }
                finally { setBusy(false); }
              }}
            />
          )}
          {err && <div className="mt-2 font-mono text-[11px]" style={{ color: COLORS.rejected }}>{err}</div>}
          <ul className="mt-3 divide-y rounded-sm border bg-panel" style={{ borderColor: COLORS.hair }}>
            {members.map((m) => (
              <li key={m.id} className="flex items-center justify-between px-4 py-2.5">
                <div>
                  <div className="text-[14px]">{m.full_name ?? "n/a"}</div>
                  <div className="font-mono text-[11px] text-ink-dim">{m.email}</div>
                </div>
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-dim">
                  {m.roles.join(" · ") || "n/a"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}

function InviteForm({ busy, onSubmit }: { busy: boolean; onSubmit: (v: { email: string; password: string; fullName: string }) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit({ email, password, fullName }); }}
      className="grid gap-2 rounded-sm border bg-panel2 p-3 sm:grid-cols-4"
      style={{ borderColor: COLORS.hair }}
    >
      <input className="rounded-sm border bg-panel px-2 py-1.5 text-[13px]" style={{ borderColor: COLORS.hair }}
        placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
      <input className="rounded-sm border bg-panel px-2 py-1.5 text-[13px]" style={{ borderColor: COLORS.hair }}
        placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input className="rounded-sm border bg-panel px-2 py-1.5 text-[13px]" style={{ borderColor: COLORS.hair }}
        placeholder="Temp password (8+)" type="text" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
      <button disabled={busy} type="submit" className="rounded-sm px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] disabled:opacity-50"
        style={{ background: COLORS.ink, color: COLORS.panel }}>
        {busy ? "..." : "Add lawyer"}
      </button>
    </form>
  );
}
