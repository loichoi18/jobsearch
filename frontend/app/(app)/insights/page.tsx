"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  SkillGapInsight,
  SkillGapsResponse,
  UpskillPlan,
} from "@/lib/types";

function requiredHeavy(gap: SkillGapInsight): boolean {
  return gap.required_count >= gap.preferred_count;
}

function GapBar({
  gap,
  maxImpact,
  onClick,
}: {
  gap: SkillGapInsight;
  maxImpact: number;
  onClick: () => void;
}) {
  const width = maxImpact > 0 ? (gap.impact / maxImpact) * 100 : 0;
  const heavy = requiredHeavy(gap);
  return (
    <button
      onClick={onClick}
      className="group w-full rounded-md px-2 py-1.5 text-left hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium">{gap.skill}</span>
        <span className="text-xs text-muted-foreground">
          {gap.frequency} job{gap.frequency === 1 ? "" : "s"} ·{" "}
          {Math.round(gap.pct_of_jobs * 100)}% · impact{" "}
          <span style={{ fontVariantNumeric: "tabular-nums" }}>
            {gap.impact}
          </span>
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-muted">
        <div
          className={cn(
            "h-2.5 rounded-full",
            heavy ? "bg-red-500" : "bg-amber-500"
          )}
          style={{ width: `${Math.max(width, 4)}%` }}
        />
      </div>
    </button>
  );
}

function GapDrawer({
  gap,
  plan,
  planLoading,
  planError,
  onGeneratePlan,
  onClose,
}: {
  gap: SkillGapInsight;
  plan: UpskillPlan | null;
  planLoading: boolean;
  planError: string | null;
  onGeneratePlan: () => void;
  onClose: () => void;
}) {
  const item = plan?.items.find(
    (i) => i.skill.toLowerCase() === gap.skill.toLowerCase()
  );
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-md overflow-y-auto border-l bg-background p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={`${gap.skill} details`}
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold">{gap.skill}</h3>
            <p className="text-sm text-muted-foreground">
              {gap.required_count} required · {gap.preferred_count} preferred
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            ✕
          </Button>
        </div>

        <h4 className="mb-2 text-sm font-medium">Jobs demanding it</h4>
        <ul className="mb-6 space-y-2">
          {gap.evidence.map((e, i) => (
            <li key={i} className="rounded-md border p-3 text-sm">
              <Link
                href={`/jobs/${e.job_id}`}
                className="font-medium text-primary hover:underline"
              >
                {e.job_title}
                {e.company ? ` — ${e.company}` : ""}
              </Link>
              <p className="mt-1 text-xs text-muted-foreground">
                “{e.phrase}”{" "}
                <span
                  className={cn(
                    "ml-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                    e.importance === "required"
                      ? "bg-red-100 text-red-700"
                      : "bg-amber-100 text-amber-700"
                  )}
                >
                  {e.importance}
                </span>
              </p>
            </li>
          ))}
        </ul>

        <h4 className="mb-2 text-sm font-medium">Upskill plan</h4>
        {item ? (
          <div className="space-y-3 text-sm">
            <p>
              <span className="font-medium">Why it matters: </span>
              {item.why_it_matters}
            </p>
            <p className="whitespace-pre-wrap">
              <span className="font-medium">2–4 week path: </span>
              {item.learning_path}
            </p>
            <p className="rounded-md bg-muted/60 p-3">
              <span className="font-medium">Portfolio project: </span>
              {item.project_idea}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              {planLoading
                ? "Generating your plan (one LLM call for all top gaps)…"
                : plan
                  ? "This skill isn't in the current plan — regenerate after your job set changes."
                  : "No plan generated yet."}
            </p>
            {planError && <p className="text-sm text-red-600">{planError}</p>}
            <Button size="sm" onClick={onGeneratePlan} disabled={planLoading}>
              {planLoading ? "Generating…" : "Generate upskill plan"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function InsightsPage() {
  const [data, setData] = useState<SkillGapsResponse | null>(null);
  const [selected, setSelected] = useState<SkillGapInsight | null>(null);
  const [plan, setPlan] = useState<UpskillPlan | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await apiFetch("/api/insights/skill-gaps");
    if (res.ok) setData(await res.json());
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function generatePlan() {
    setPlanLoading(true);
    setPlanError(null);
    const res = await apiFetch("/api/insights/upskill-plan", {
      method: "POST",
    });
    setPlanLoading(false);
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setPlanError(
        typeof body?.detail === "string"
          ? body.detail
          : "Plan generation failed — try again."
      );
      return;
    }
    setPlan(await res.json());
  }

  const maxImpact = data?.gaps[0]?.impact ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Skill gaps</h2>
        <p className="text-muted-foreground">
          Missing skills across your {data?.jobs_analyzed ?? "—"} analyzed
          jobs, sorted by impact (red = mostly required, amber = mostly
          preferred). Click a skill for details.
        </p>
      </div>

      <Card>
        <CardContent className="p-4">
          {!data ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : data.gaps.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No gaps yet — analyze some saved jobs first (Jobs → open a job →
              Analyze).
            </p>
          ) : (
            <div className="space-y-1">
              {data.gaps.map((gap) => (
                <GapBar
                  key={gap.skill}
                  gap={gap}
                  maxImpact={maxImpact}
                  onClick={() => setSelected(gap)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selected && (
        <GapDrawer
          gap={selected}
          plan={plan}
          planLoading={planLoading}
          planError={planError}
          onGeneratePlan={generatePlan}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
