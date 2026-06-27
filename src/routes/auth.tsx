import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useServerFn } from "@tanstack/react-start";
import { createFirmWithDemo } from "@/lib/firm.functions";
import { COLORS } from "@/lib/pleading";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — Coherence Console" },
      { name: "description", content: "Sign in to your cabinet to manage cases." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const createFirm = useServerFn(createFirmWithDemo);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) navigate({ to: "/cases" });
    });
  }, [navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { full_name: fullName },
            emailRedirectTo: window.location.origin + "/cases",
          },
        });
        if (error) throw error;
        if (!data.session) {
          // Email confirm required
          setErr("Check your email to confirm, then sign in.");
          setMode("signin");
          return;
        }
        await createFirm({ data: { firmName, fullName } });
        navigate({ to: "/cases" });
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        navigate({ to: "/cases" });
      }
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg text-ink">
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-12">
        <Link to="/" className="mb-8 font-mono text-[10px] uppercase tracking-[0.3em] text-ink-dim hover:text-ink">
          ← Pleading-to-Proof
        </Link>
        <div className="rounded-sm border bg-panel p-7" style={{ borderColor: COLORS.hair }}>
          <h1 className="font-display text-[22px] leading-tight">
            {mode === "signin" ? "Sign in" : "Open a cabinet"}
          </h1>
          <p className="mt-1 font-mono text-[11px] text-ink-dim">
            {mode === "signin" ? "Access your firm's case files." : "Create your firm and start with a demo case."}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-3">
            {mode === "signup" && (
              <>
                <Field label="Your name" value={fullName} onChange={setFullName} required />
                <Field label="Cabinet / Firm name" value={firmName} onChange={setFirmName} required />
              </>
            )}
            <Field label="Email" type="email" value={email} onChange={setEmail} required />
            <Field label="Password" type="password" value={password} onChange={setPassword} required minLength={8} />

            {err && (
              <div className="rounded-sm border px-3 py-2 text-[12px]" style={{ borderColor: COLORS.rejected, color: COLORS.rejected }}>
                {err}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-sm px-3 py-2.5 font-mono text-[11px] uppercase tracking-[0.2em] disabled:opacity-50"
              style={{ background: COLORS.ink, color: COLORS.panel }}
            >
              {loading ? "…" : mode === "signin" ? "Sign in" : "Create cabinet"}
            </button>
          </form>

          <button
            type="button"
            onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
            className="mt-5 w-full font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim hover:text-ink"
          >
            {mode === "signin" ? "No account? Open a cabinet →" : "← Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label, value, onChange, type = "text", required, minLength,
}: { label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean; minLength?: number }) {
  return (
    <label className="block">
      <span className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        minLength={minLength}
        className="mt-1 w-full rounded-sm border bg-panel2 px-3 py-2 text-[14px] text-ink outline-none focus:border-ink"
        style={{ borderColor: COLORS.hair }}
      />
    </label>
  );
}
