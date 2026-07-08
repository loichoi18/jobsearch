import { describe, expect, it } from "vitest";
import { computeStats, daysSince, needsFollowUp } from "./stats";
import type { Job } from "./types";

const NOW = new Date("2026-07-06T00:00:00Z");

function job(overrides: Partial<Job>): Job {
  return {
    id: Math.random().toString(36).slice(2),
    source: "manual",
    title: "T",
    company: null,
    location: null,
    description: null,
    url: null,
    salary_min: null,
    salary_max: null,
    status: "saved",
    match_score: null,
    skill_gaps: null,
    applied_at: null,
    updated_at: null,
    created_at: null,
    ...overrides,
  };
}

describe("daysSince", () => {
  it("returns whole days", () => {
    expect(daysSince("2026-07-01T00:00:00Z", NOW)).toBe(5);
  });
  it("handles null and garbage", () => {
    expect(daysSince(null, NOW)).toBeNull();
    expect(daysSince("not-a-date", NOW)).toBeNull();
  });
});

describe("needsFollowUp", () => {
  it("flags applied cards older than 14 days", () => {
    expect(
      needsFollowUp(
        job({ status: "applied", applied_at: "2026-06-20T00:00:00Z" }),
        NOW
      )
    ).toBe(true);
  });
  it("does not flag recent or non-applied cards", () => {
    expect(
      needsFollowUp(
        job({ status: "applied", applied_at: "2026-07-01T00:00:00Z" }),
        NOW
      )
    ).toBe(false);
    expect(
      needsFollowUp(
        job({ status: "interview", applied_at: "2026-01-01T00:00:00Z" }),
        NOW
      )
    ).toBe(false);
  });
});

describe("computeStats", () => {
  const jobs: Job[] = [
    job({ status: "saved" }),
    job({ status: "saved", match_score: 90 }), // saved scores don't count
    job({
      status: "applied",
      applied_at: "2026-07-03T00:00:00Z",
      match_score: 80,
    }),
    job({
      status: "applied",
      applied_at: "2026-06-01T00:00:00Z",
      match_score: 60,
    }),
    job({
      status: "interview",
      applied_at: "2026-06-20T00:00:00Z",
      match_score: 70,
    }),
    job({ status: "rejected", applied_at: "2026-06-10T00:00:00Z" }),
  ];

  it("computes the strip", () => {
    const stats = computeStats(jobs, NOW);
    expect(stats.total).toBe(6);
    expect(stats.appliedThisWeek).toBe(1); // only the 2026-07-03 one
    expect(stats.interviewRate).toBeCloseTo(1 / 4); // 1 interview of 4 applied
    expect(stats.avgAppliedScore).toBeCloseTo((80 + 60 + 70) / 3);
  });

  it("returns nulls when nothing applied", () => {
    const stats = computeStats([job({ status: "saved" })], NOW);
    expect(stats.interviewRate).toBeNull();
    expect(stats.avgAppliedScore).toBeNull();
  });
});
