/** Pure stat/tracking helpers for the dashboard (unit-tested with vitest). */

import type { Job } from "@/lib/types";

export const FOLLOW_UP_DAYS = 14;
const MS_PER_DAY = 86_400_000;

export interface DashboardStats {
  total: number;
  appliedThisWeek: number;
  /** interviews (incl. offers) / everything that has been applied; null when nothing applied */
  interviewRate: number | null;
  /** mean match score of applied-or-later jobs with a score; null when none */
  avgAppliedScore: number | null;
}

export function daysSince(iso: string | null, now: Date = new Date()): number | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  return Math.max(0, Math.floor((now.getTime() - then) / MS_PER_DAY));
}

/** A job counts as "applied" if it ever left Saved (or has an applied_at). */
export function hasApplied(job: Job): boolean {
  return job.applied_at != null || job.status !== "saved";
}

export function needsFollowUp(job: Job, now: Date = new Date()): boolean {
  if (job.status !== "applied") return false;
  const days = daysSince(job.applied_at, now);
  return days !== null && days >= FOLLOW_UP_DAYS;
}

export function computeStats(jobs: Job[], now: Date = new Date()): DashboardStats {
  const applied = jobs.filter(hasApplied);
  const appliedThisWeek = applied.filter((j) => {
    const days = daysSince(j.applied_at, now);
    return days !== null && days < 7;
  }).length;

  const interviews = applied.filter(
    (j) => j.status === "interview" || j.status === "offer"
  ).length;
  const interviewRate =
    applied.length > 0 ? interviews / applied.length : null;

  const scored = applied.filter((j) => j.match_score != null);
  const avgAppliedScore =
    scored.length > 0
      ? scored.reduce((sum, j) => sum + (j.match_score as number), 0) /
        scored.length
      : null;

  return {
    total: jobs.length,
    appliedThisWeek,
    interviewRate,
    avgAppliedScore,
  };
}
