import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { COLORS } from "@/lib/pleading";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Pleading-to-Proof — Coherence Console" },
      {
        name: "description",
        content:
          "A litigation pleading at the centre of an evidence knowledge graph. See which allegations stand, which fall, and why.",
      },
      { property: "og:title", content: "Pleading-to-Proof — Coherence Console" },
      {
        property: "og:description",
        content: "Pleading at the centre, evidence around it — colour-coded by judgment.",
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
          <div className="font-mono text-[11px] uppercase tracking-[0.28em]">Pleading-to-Proof</div>
          {checked && (
            signedIn ? (
              <Link to="/cases" className="font-mono text-[10px] uppercase tracking-[0.22em] underline">
                My cases →
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
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-ink-dim">Coherence Console</p>
        <h1 className="mt-3 font-display text-[40px] leading-[1.1] sm:text-[56px]">
          The pleading at the <em className="font-normal">centre</em> — the evidence around it.
        </h1>
        <p className="mt-6 max-w-2xl text-[15px] leading-relaxed text-ink-dim">
          Each pleaded allegation sits in the middle of a force-directed graph of the documents and claims that support
          or contradict it. Two modes — <span className="text-ink">Pleading Stress Test</span> and{" "}
          <span className="text-ink">Bundle Coherence</span> — show you which allegations stand, which fall, and why.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <button
            onClick={() => navigate({ to: signedIn ? "/cases" : "/auth" })}
            className="rounded-sm px-5 py-3 font-mono text-[11px] uppercase tracking-[0.2em]"
            style={{ background: COLORS.ink, color: COLORS.panel }}
          >
            {signedIn ? "Open my cases →" : "Open a cabinet →"}
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
          <Feature title="Cabinet & lawyers" body="Open your firm in one click. Invite your team. Every case is shared inside the cabinet." />
          <Feature title="Three views, one truth" body="Document-style Pleading and Bundle on the side; force-directed Graph when you need the whole web at once." />
          <Feature title="Colour by judgment" body="Green stands, red falls, amber is a legal overlay, slate is unaddressed. Brass rings flag load-bearing evidence." />
        </div>
      </main>

      <footer className="border-t px-6 py-4 text-center font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim"
        style={{ borderColor: COLORS.hair, background: COLORS.panel }}>
        Forensic · pleading-centred · issue-local
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
