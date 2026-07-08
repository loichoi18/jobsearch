"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DocumentsPanel } from "@/components/jobs/documents-panel";
import { MatchAnalysisPanel } from "@/components/jobs/match-analysis";
import { StatusBadge } from "@/components/jobs/status-badge";
import { apiFetch } from "@/lib/api";
import {
  JOB_STATUSES,
  type Job,
  type JobStatus,
  type MatchAnalysis,
} from "@/lib/types";

function formatSalary(min: number | null, max: number | null): string | null {
  if (!min && !max) return null;
  const fmt = (n: number) => `$${Math.round(n / 1000)}k`;
  if (min && max) return `${fmt(min)}–${fmt(max)}`;
  return fmt((min ?? max) as number);
}

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    const res = await apiFetch(`/api/jobs/${params.id}`);
    if (res.ok) setJob(await res.json());
    else setNotFound(true);
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function setStatus(status: JobStatus) {
    if (!job) return;
    const previous = job;
    setJob({ ...job, status });
    const res = await apiFetch(`/api/jobs/${job.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) setJob(previous);
  }

  async function remove() {
    if (!job) return;
    const res = await apiFetch(`/api/jobs/${job.id}`, { method: "DELETE" });
    if (res.ok) router.push("/jobs");
  }

  if (notFound) {
    return <p className="text-muted-foreground">Job not found.</p>;
  }
  if (!job) {
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const salary = formatSalary(job.salary_min, job.salary_max);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">{job.title}</h2>
          <p className="text-muted-foreground">
            {[job.company, job.location, salary].filter(Boolean).join(" · ")}
          </p>
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-primary underline underline-offset-2"
            >
              View original posting
            </a>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <StatusBadge status={job.status} />
          <select
            value={job.status}
            onChange={(e) => setStatus(e.target.value as JobStatus)}
            className="h-9 rounded-md border border-input bg-background px-2 text-sm capitalize"
            aria-label="Application status"
          >
            {JOB_STATUSES.map((s) => (
              <option key={s} value={s} className="capitalize">
                {s}
              </option>
            ))}
          </select>
          <Button variant="outline" size="sm" onClick={remove}>
            Delete
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Job description</CardTitle>
        </CardHeader>
        <CardContent>
          {job.description ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {job.description}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              No description stored for this job.
            </p>
          )}
        </CardContent>
      </Card>

      <MatchAnalysisPanel
        jobId={job.id}
        analysis={job.skill_gaps}
        onAnalyzed={(analysis: MatchAnalysis) =>
          setJob({
            ...job,
            skill_gaps: analysis,
            match_score: analysis.match_score,
          })
        }
      />
      <DocumentsPanel jobId={job.id} />
    </div>
  );
}
