"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PasteJobDialog } from "@/components/jobs/paste-job-dialog";
import { SearchPanel } from "@/components/jobs/search-panel";
import { StatusBadge } from "@/components/jobs/status-badge";
import { apiFetch } from "@/lib/api";
import type { Job } from "@/lib/types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [sortByScore, setSortByScore] = useState(false);

  const refresh = useCallback(async () => {
    const res = await apiFetch("/api/jobs");
    if (res.ok) setJobs(await res.json());
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Jobs</h2>
          <p className="text-muted-foreground">
            Search live AU listings or paste a posting from anywhere.
          </p>
        </div>
        <Button variant="outline" onClick={() => setPasteOpen(true)}>
          Paste a job
        </Button>
      </div>

      <SearchPanel onSaved={refresh} />

      <Card>
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div>
            <CardTitle>Saved jobs</CardTitle>
            <CardDescription>
              {jobs.length === 0
                ? "Nothing saved yet."
                : `${jobs.length} saved — click one to analyze and generate documents.`}
            </CardDescription>
          </div>
          {jobs.length > 1 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSortByScore((v) => !v)}
            >
              {sortByScore ? "Sort: match score ↓" : "Sort: newest"}
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <ul className="divide-y">
            {(sortByScore
              ? [...jobs].sort(
                  (a, b) => (b.match_score ?? -1) - (a.match_score ?? -1)
                )
              : jobs
            ).map((job) => (
              <li key={job.id}>
                <Link
                  href={`/jobs/${job.id}`}
                  className="flex items-center justify-between gap-4 py-3 hover:bg-muted/50"
                >
                  <div className="min-w-0">
                    <p className="font-medium">{job.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {[job.company, job.location].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    {job.match_score != null && (
                      <span className="text-sm font-semibold">
                        {Math.round(job.match_score)}
                      </span>
                    )}
                    <StatusBadge status={job.status} />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <PasteJobDialog
        open={pasteOpen}
        onClose={() => setPasteOpen(false)}
        onSaved={refresh}
      />
    </div>
  );
}
