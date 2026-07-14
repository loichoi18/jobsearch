import Link from "next/link";
import {
  BadgeCheck,
  FileSearch,
  Github,
  PenLine,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";

/** Mock of the job-detail grounding panel, framed in browser chrome —
    the product's signature interaction, shown before sign-up. */
function GroundingMock() {
  return (
    <div className="mx-auto mt-14 w-full max-w-3xl overflow-hidden rounded-xl border bg-white text-left shadow-xl">
      <div className="flex items-center gap-1.5 border-b bg-slate-50 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        <span className="ml-3 truncate rounded-md bg-white px-3 py-0.5 text-xs text-slate-400">
          jobpilot.au/jobs/ml-internship — Grounding report
        </span>
      </div>
      <div className="p-6">
        <div className="flex items-baseline gap-3">
          <span className="gradient-text tnum text-4xl font-bold">94%</span>
          <span className="text-sm font-medium text-slate-900">
            claim-grounding rate
          </span>
          <span className="text-xs text-slate-500">
            16/17 claims traceable to your profile
          </span>
        </div>
        <ul className="mt-4 space-y-2 text-sm">
          <li className="flex gap-2">
            <span className="font-bold text-emerald-600">✓</span>
            <span className="text-slate-700">
              Built an LLM evaluation harness with automated regression gates
            </span>
          </li>
          <li className="flex gap-2">
            <span className="font-bold text-emerald-600">✓</span>
            <span className="text-slate-700">
              Implemented hybrid retrieval (pgvector + full-text, RRF-fused)
            </span>
          </li>
          <li className="flex gap-2">
            <span className="font-bold text-red-600">✕</span>
            <span className="text-red-700 line-through decoration-red-400">
              Led a team of 12 engineers at a FAANG company
            </span>
          </li>
        </ul>
        <p className="mt-4 rounded-[8px] bg-red-50 px-3 py-2 text-xs text-red-700">
          1 unsupported claim was removed from the final document — it could
          not be traced to your profile.
        </p>
      </div>
    </div>
  );
}

const STEPS = [
  {
    icon: FileSearch,
    title: "Retrieve",
    text: "Your CV becomes a structured, embedded profile. Every job is matched against real evidence, hybrid dense + keyword retrieval.",
  },
  {
    icon: PenLine,
    title: "Draft + Review",
    text: "A drafter writes from retrieved evidence only. An independent reviewer critiques it against the JD with fresh context, then one revision.",
  },
  {
    icon: ShieldCheck,
    title: "Verify",
    text: "A grounding verifier audits every claim against your profile. Unsupported claims are removed, never sent.",
  },
];

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Grounding verification",
    text: "Each bullet and paragraph cites the profile chunks that back it. The verifier strips anything it can't trace, and shows you the report.",
  },
  {
    icon: PenLine,
    title: "Drafter–reviewer loop",
    text: "Two independent model roles: one writes, one recruits-screens the draft against the job description before revision.",
  },
  {
    icon: BadgeCheck,
    title: "Skill-gap intelligence",
    text: "Missing skills aggregated across every saved job, weighted by how often, and how hard, employers demand them.",
  },
];

export default function LandingPage() {
  return (
    <main className="bg-white text-slate-900">
      {/* Sticky nav */}
      <header className="sticky top-0 z-40 border-b bg-white/80 backdrop-blur">
        <nav className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <span className="font-semibold tracking-tight">JobPilot AU</span>
          <div className="flex items-center gap-4">
            <a
              href="#how"
              className="hidden text-sm text-slate-600 hover:text-slate-900 sm:block"
            >
              How it works
            </a>
            <a
              href="#features"
              className="hidden text-sm text-slate-600 hover:text-slate-900 sm:block"
            >
              Features
            </a>
            <Button asChild size="sm">
              <Link href="/login">Get started</Link>
            </Button>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Soft decorative blobs (brand gradient allowance) */}
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 left-1/2 h-96 w-96 -translate-x-[70%] rounded-full bg-indigo-400/15 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute top-10 left-1/2 h-80 w-80 translate-x-[20%] rounded-full bg-violet-400/15 blur-3xl"
        />
        <div className="relative mx-auto max-w-5xl px-6 pb-20 pt-16 text-center sm:pt-24">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
            <Sparkles className="h-3 w-3" aria-hidden />
            Grounded &amp; evaluated, not a wrapper
          </span>
          <h1 className="mx-auto mt-5 max-w-3xl text-4xl font-bold tracking-[-0.02em] sm:text-[56px] sm:leading-[1.1]">
            Job applications the model{" "}
            <span className="gradient-text">can&apos;t make up</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-slate-600">
            Tailored CVs and cover letters for the Australian graduate market,
            drafted from your real profile, reviewed against the JD, and
            verified claim by claim.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/login">Start applying</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <a href="#how">See how it works</a>
            </Button>
          </div>
          <GroundingMock />
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t bg-slate-50">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <h2 className="text-center text-3xl font-bold tracking-[-0.02em]">
            Retrieve → Draft + Review → Verify
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-center text-slate-600">
            The pipeline is the product: three model roles with separated
            contexts, so no single prompt gets to grade its own homework.
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }, i) => (
              <div key={title} className="rounded-xl border bg-white p-6 shadow-sm">
                <div className="flex h-10 w-10 items-center justify-center rounded-[8px] bg-indigo-100">
                  <Icon className="h-5 w-5 text-indigo-600" aria-hidden />
                </div>
                <h3 className="mt-4 font-semibold">
                  {i + 1}. {title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">
                  {text}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-5xl px-6 py-20">
        <div className="grid gap-6 sm:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div
              key={title}
              className="rounded-xl border bg-white p-6 shadow-sm transition-shadow motion-safe:hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-[8px] bg-indigo-100">
                <Icon className="h-5 w-5 text-indigo-600" aria-hidden />
              </div>
              <h3 className="mt-4 font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                {text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Eval metrics band */}
      <section className="border-t bg-slate-50">
        <div className="mx-auto grid max-w-5xl gap-8 px-6 py-16 text-center sm:grid-cols-3">
          <div>
            <p className="gradient-text tnum text-4xl font-bold">100%</p>
            <p className="mt-1 text-sm text-slate-600">
              of claims audited against your profile
            </p>
          </div>
          <div>
            <p className="gradient-text tnum text-4xl font-bold">0</p>
            <p className="mt-1 text-sm text-slate-600">
              unsupported claims shipped, removed by construction
            </p>
          </div>
          <div>
            <p className="gradient-text tnum text-4xl font-bold">25</p>
            <p className="mt-1 text-sm text-slate-600">
              cases in the regression eval set, run on every change
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-3 px-6 py-10 text-center sm:flex-row sm:justify-between sm:text-left">
          <p className="text-sm text-slate-600">
            JobPilot AU — a grounded drafting assistant with human review.
            Never an auto-applier: you edit and send every application
            yourself.
          </p>
          <a
            href="https://github.com/"
            className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900"
          >
            <Github className="h-4 w-4" aria-hidden />
            GitHub
          </a>
        </div>
      </footer>
    </main>
  );
}
