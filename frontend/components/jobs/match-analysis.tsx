"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { MatchAnalysis, MissingSkill } from "@/lib/types";

interface Props {
  jobId: string;
  analysis: MatchAnalysis | null;
  onAnalyzed: (analysis: MatchAnalysis) => void;
}

/** Radial score dial, 0-100. */
function ScoreDial({ score }: { score: number }) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.max(0, Math.min(100, score)) / 100) * circumference;
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" role="img" aria-label={`Match score ${Math.round(score)} out of 100`}>
      <defs>
        <linearGradient id="dial-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#6366F1" />
          <stop offset="100%" stopColor="#8B5CF6" />
        </linearGradient>
      </defs>
      <circle cx="60" cy="60" r={radius} fill="none" strokeWidth="10" className="stroke-slate-100" />
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${filled} ${circumference - filled}`}
        transform="rotate(-90 60 60)"
        stroke="url(#dial-gradient)"
      />
      <text x="60" y="66" textAnchor="middle" className="fill-foreground text-2xl font-bold" style={{ fontVariantNumeric: "tabular-nums" }}>
        {Math.round(score)}
      </text>
    </svg>
  );
}

const CRITERIA: { key: keyof MatchAnalysis["breakdown"]; label: string }[] = [
  { key: "technical_skills", label: "Technical skills" },
  { key: "experience_relevance", label: "Experience relevance" },
  { key: "education_fit", label: "Education fit" },
  { key: "nice_to_haves", label: "Nice-to-haves" },
];

function GapChip({ skill }: { skill: MissingSkill }) {
  const required = skill.importance === "required";
  return (
    <span
      title={`JD: “${skill.evidence}”`}
      className={cn(
        "inline-flex cursor-help items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        required ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
      )}
    >
      {skill.name}
    </span>
  );
}

export function MatchAnalysisPanel({ jobId, analysis, onAnalyzed }: Props) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyze() {
    setRunning(true);
    setError(null);
    const res = await apiFetch(`/api/jobs/${jobId}/analyze`, {
      method: "POST",
    });
    setRunning(false);
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(
        typeof body?.detail === "string"
          ? body.detail
          : "Analysis failed — try again shortly."
      );
      return;
    }
    onAnalyzed(await res.json());
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle>Match analysis</CardTitle>
          <CardDescription>
            Semantic similarity (30%) + LLM rubric against your profile (70%).
          </CardDescription>
        </div>
        <Button size="sm" variant="outline" onClick={analyze} disabled={running}>
          {running ? "Analyzing…" : analysis ? "Re-analyze" : "Analyze"}
        </Button>
      </CardHeader>
      <CardContent>
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        {!analysis ? (
          <p className="text-sm text-muted-foreground">
            {running
              ? "Scoring this job against your profile…"
              : "Not analyzed yet — run the analysis to see your match score and skill gaps."}
          </p>
        ) : (
          <div className="space-y-5">
            {analysis.short_description && (
              <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                This job&apos;s stored description looks truncated (likely an
                Adzuna snippet). Paste the full JD for a reliable score.
              </p>
            )}

            <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
              <ScoreDial score={analysis.match_score} />
              <div className="flex-1 space-y-2">
                {CRITERIA.map(({ key, label }) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{label}</span>
                      <span style={{ fontVariantNumeric: "tabular-nums" }}>
                        {analysis.breakdown[key]}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted">
                      <div
                        className="h-1.5 rounded-full bg-primary"
                        style={{ width: `${analysis.breakdown[key]}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <p className="text-sm italic text-muted-foreground">
              “{analysis.one_line_verdict}”
            </p>

            <div>
              <h4 className="mb-2 text-sm font-medium">Matched skills</h4>
              <div className="flex flex-wrap gap-1.5">
                {analysis.matched_skills.length === 0 ? (
                  <span className="text-sm text-muted-foreground">None found.</span>
                ) : (
                  analysis.matched_skills.map((s) => (
                    <span
                      key={s}
                      className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700"
                    >
                      {s}
                    </span>
                  ))
                )}
              </div>
            </div>

            <div>
              <h4 className="mb-2 text-sm font-medium">
                Missing skills{" "}
                <span className="font-normal text-muted-foreground">
                  (red = required, amber = preferred — hover for the JD phrase)
                </span>
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {analysis.missing_skills.length === 0 ? (
                  <span className="text-sm text-muted-foreground">
                    No gaps detected.
                  </span>
                ) : (
                  analysis.missing_skills.map((s) => (
                    <GapChip key={s.name} skill={s} />
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
