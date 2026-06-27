import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { COLORS } from "@/lib/pleading";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "PleadProof" },
      {
        name: "description",
        content:
          "Check every pleaded allegation against the evidence in the bundle. See what holds, what falls, and why.",
      },
      { property: "og:title", content: "PleadProof" },
      {
        property: "og:description",
        content: "Every allegation checked against the evidence, colour-coded by verdict.",
      },
    ],
  }),
  component: Landing,
});

function Landing() {
  const navigate = useNavigate();
  const [checked, setChecked] = useState(false);
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setSignedIn(!!data.user);
      setChecked(true);
    });
  }, []);

  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="border-b px-6 py-4" style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div className="font-mono text-[11px] uppercase tracking-[0.28em]">PleadProof</div>
          {checked && (
            signedIn ? (
              <Link to="/cases" className="font-mono text-[10px] uppercase tracking-[0.22em] underline">
                My cases
              </Link>
            ) : (
              <Link to="/auth" className="font-mono text-[10px] uppercase tracking-[0.22em] underline">
                Sign in
              </Link>
            )
          )}
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-20">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-ink-dim">PleadProof</p>
        <h1 className="mt-3 font-display text-[40px] leading-[1.1] sm:text-[56px]">
          See which allegations hold, and which fall.
        </h1>
        <p className="mt-6 max-w-2xl text-[15px] leading-relaxed text-ink-dim">
          Every pleaded allegation is checked against the evidence in the bundle. The graph shows what supports it,
          what contradicts it, and why.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <button
            onClick={() => navigate({ to: signedIn ? "/cases" : "/auth" })}
            className="rounded-sm px-5 py-3 font-mono text-[11px] uppercase tracking-[0.2em]"
            style={{ background: COLORS.ink, color: COLORS.panel }}
          >
            {signedIn ? "Open my cases" : "Get started"}
          </button>
          <Link
            to="/auth"
            className="rounded-sm border px-5 py-3 font-mono text-[11px] uppercase tracking-[0.2em]"
            style={{ borderColor: COLORS.hair }}
          >
            Sign in
          </Link>
        </div>

        <div className="mt-16 grid gap-6 sm:grid-cols-3">
          <Feature title="Your firm" body="Create your firm and invite your team. Every case is shared across it." />
          <Feature title="Two ways to read it" body="Read the pleading and bundle as documents, or open the graph to see the whole network at once." />
          <Feature title="Colour by verdict" body="Green holds, red falls, amber is a legal limit, grey is unproven. A gold ring marks evidence the case leans on." />
        </div>
      </main>

      <footer className="border-t px-6 py-4 text-center font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim"
        style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
        PleadProof
      </footer>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-sm border bg-panel p-4" style={{ borderColor: COLORS.hair }}>
      <div className="font-display text-[15px]">{title}</div>
      <p className="mt-2 text-[13px] leading-relaxed text-ink-dim">{body}</p>
    </div>
  );
}
