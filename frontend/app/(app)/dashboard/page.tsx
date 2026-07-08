"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { KanbanBoard } from "@/components/dashboard/kanban";
import { apiFetch } from "@/lib/api";
import { computeStats } from "@/lib/stats";
import type { Job } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p
          className="text-2xl font-bold"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {value}
        </p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    const res = await apiFetch("/api/jobs");
    if (res.ok) setJobs(await res.json());
    setLoaded(true);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = computeStats(jobs);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Drag cards between columns to track your applications.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Total saved" value={String(stats.total)} />
        <Stat label="Applied this week" value={String(stats.appliedThisWeek)} />
        <Stat
          label="Interview rate"
          value={
            stats.interviewRate === null
              ? "—"
              : `${Math.round(stats.interviewRate * 100)}%`
          }
        />
        <Stat
          label="Avg match score (applied)"
          value={
            stats.avgAppliedScore === null
              ? "—"
              : String(Math.round(stats.avgAppliedScore))
          }
        />
      </div>

      {loaded && jobs.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No jobs yet — save some from the Jobs page to start tracking.
        </p>
      ) : (
        <KanbanBoard jobs={jobs} onJobsChange={setJobs} />
      )}
    </div>
  );
}
