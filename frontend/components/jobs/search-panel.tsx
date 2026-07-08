"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { cityOf } from "@/lib/locations";
import type { JobSearchResponse, JobSearchResult } from "@/lib/types";

function formatSalary(min: number | null, max: number | null): string | null {
  if (!min && !max) return null;
  const fmt = (n: number) => `$${Math.round(n / 1000)}k`;
  if (min && max) return `${fmt(min)}–${fmt(max)}`;
  return fmt((min ?? max) as number);
}

export function SearchPanel({ onSaved }: { onSaved: () => void }) {
  const [what, setWhat] = useState("machine learning internship");
  const [where, setWhere] = useState("");
  const [results, setResults] = useState<JobSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());

  // Default the location filter from the user's preferred locations.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch("/api/profile");
        if (!res.ok || cancelled) return;
        const body = await res.json();
        const locs: string[] = body?.structured?.preferred_locations ?? [];
        if (locs.length > 0) setWhere((w) => (w ? w : cityOf(locs[0])));
      } catch {
        /* best-effort default; ignore if the backend isn't reachable */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const UNREACHABLE =
    "Couldn't reach the server. It may be waking up (free tier can take ~50s) " +
    "or NEXT_PUBLIC_API_URL isn't set. Try again in a moment.";

  async function search() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ what, where, page: "1" });
      const res = await apiFetch(`/api/jobs/search?${params}`);
      if (!res.ok) {
        setError(
          "Search failed — Adzuna may be rate-limited. Try again shortly."
        );
        return;
      }
      const body: JobSearchResponse = await res.json();
      setResults(body.results);
    } catch {
      setError(UNREACHABLE);
    } finally {
      setLoading(false);
    }
  }

  async function save(result: JobSearchResult) {
    setSavingId(result.adzuna_id);
    setError(null);
    try {
      const res = await apiFetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: "adzuna", payload: result }),
      });
      if (res.ok) {
        setSavedIds((prev) => new Set(prev).add(result.adzuna_id));
        onSaved();
      } else {
        setError("Couldn't save that job. Try again shortly.");
      }
    } catch {
      setError(UNREACHABLE);
    } finally {
      setSavingId(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search Australian listings</CardTitle>
        <CardDescription>
          Live graduate/internship roles via the Adzuna API.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            value={what}
            onChange={(e) => setWhat(e.target.value)}
            placeholder="e.g. AI internship"
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <Input
            value={where}
            onChange={(e) => setWhere(e.target.value)}
            placeholder="Location (e.g. Sydney)"
            className="sm:max-w-[200px]"
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <Button onClick={search} disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </Button>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <ul className="divide-y">
          {results.map((r) => {
            const salary = formatSalary(r.salary_min, r.salary_max);
            const saved = savedIds.has(r.adzuna_id);
            return (
              <li
                key={r.adzuna_id}
                className="flex items-start justify-between gap-4 py-3"
              >
                <div className="min-w-0">
                  <p className="font-medium">{r.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {[r.company, r.location, salary]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  {r.snippet && (
                    <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                      {r.snippet}
                    </p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant={saved ? "outline" : "default"}
                  disabled={saved || savingId === r.adzuna_id}
                  onClick={() => save(r)}
                >
                  {saved ? "Saved" : savingId === r.adzuna_id ? "…" : "Save"}
                </Button>
              </li>
            );
          })}
        </ul>
        {!loading && results.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Run a search to see live listings.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
