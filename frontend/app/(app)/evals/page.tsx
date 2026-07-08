"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Terminal } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { EvalRun } from "@/lib/types";

const num = { fontVariantNumeric: "tabular-nums" } as const;
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/** Inline SVG sparkline of a metric across runs (oldest → newest). */
function Trend({ values }: { values: number[] }) {
  if (values.length < 2) {
    return <span className="text-xs text-slate-400">Not enough runs yet</span>;
  }
  const w = 160;
  const h = 40;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / span) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline
        points={pts}
        fill="none"
        stroke="#4F46E5"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Kpi({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "emerald" | "red" | "indigo";
}) {
  const toneClass = {
    emerald: "text-emerald-600",
    red: "text-red-600",
    indigo: "text-indigo-600",
  }[tone];
  return (
    <Card>
      <CardContent className="p-6">
        <div className="text-sm text-slate-500">{label}</div>
        <div className={cn("mt-1 text-3xl font-bold", toneClass)} style={num}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
          <Terminal className="h-6 w-6 text-indigo-600" />
        </div>
        <p className="max-w-md text-sm text-slate-600">
          No evaluation runs yet. Run the harness to populate this page:
        </p>
        <code className="rounded-md bg-slate-900 px-3 py-1.5 text-xs text-slate-100">
          python -m evaluation.harness --dataset v1 --persist
        </code>
        <p className="max-w-md text-xs text-slate-400">
          Add <span className="font-mono">--mock</span> to run for free with the
          deterministic provider (no API keys, no cost).
        </p>
      </CardContent>
    </Card>
  );
}

export default function EvalsPage() {
  const [runs, setRuns] = useState<EvalRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch("/api/evals/runs");
      if (!res.ok) throw new Error(`Failed to load runs (${res.status})`);
      setRuns((await res.json()) as EvalRun[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load eval runs");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">
          Evaluation
        </h2>
        <p className="text-slate-600">
          Grounding, fabrication, and keyword coverage across the golden
          dataset — the guarantee that generated documents don&apos;t make
          things up.
        </p>
      </div>

      {error && (
        <Card>
          <CardContent className="p-6 text-sm text-red-600">{error}</CardContent>
        </Card>
      )}

      {runs === null && !error && (
        <div className="text-sm text-slate-400">Loading runs…</div>
      )}

      {runs !== null && runs.length === 0 && <EmptyState />}

      {runs !== null && runs.length > 0 && <EvalContent runs={runs} />}
    </div>
  );
}

function EvalContent({ runs }: { runs: EvalRun[] }) {
  // API returns newest first; oldest→newest for the trend line.
  const latest = runs[0];
  const agg = latest.metrics.aggregate;
  const groundingSeries = [...runs]
    .reverse()
    .map((r) => r.metrics.aggregate.grounding_rate);

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-3">
        <Kpi label="Grounding rate" value={pct(agg.grounding_rate)} tone="emerald" />
        <Kpi
          label="Fabrication rate"
          value={pct(agg.fabrication_rate)}
          tone={agg.fabrication_rate > 0 ? "red" : "emerald"}
        />
        <Kpi
          label="Keyword coverage"
          value={pct(agg.keyword_coverage)}
          tone="indigo"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="p-6">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">
                Recent runs
              </h3>
              <span className="text-xs text-slate-400">
                dataset {latest.dataset_version}
                {latest.metrics.mock ? " · mock" : ""}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2 font-medium">Date</th>
                    <th className="px-3 py-2 font-medium">Cases</th>
                    <th className="px-3 py-2 font-medium">Grounding</th>
                    <th className="px-3 py-2 font-medium">Fabrication</th>
                    <th className="px-3 py-2 font-medium">Keywords</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id} className="border-b border-slate-100">
                      <td className="px-3 py-2 text-slate-600">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-3 py-2" style={num}>
                        {r.metrics.aggregate.cases}
                      </td>
                      <td className="px-3 py-2 text-emerald-600" style={num}>
                        {pct(r.metrics.aggregate.grounding_rate)}
                      </td>
                      <td
                        className={cn(
                          "px-3 py-2",
                          r.metrics.aggregate.fabrication_rate > 0
                            ? "text-red-600"
                            : "text-slate-600"
                        )}
                        style={num}
                      >
                        {pct(r.metrics.aggregate.fabrication_rate)}
                      </td>
                      <td className="px-3 py-2 text-slate-600" style={num}>
                        {pct(r.metrics.aggregate.keyword_coverage)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-900">
              Grounding rate trend
            </h3>
            <Trend values={groundingSeries} />
            <p className="mt-3 text-xs text-slate-400">
              Across {runs.length} run{runs.length === 1 ? "" : "s"}. The CI gate
              fails any run below 85%.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-6">
          <h3 className="mb-3 text-sm font-semibold text-slate-900">
            Latest run — per case
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2 font-medium">Case</th>
                  <th className="px-3 py-2 font-medium">Type</th>
                  <th className="px-3 py-2 font-medium">Grounding</th>
                  <th className="px-3 py-2 font-medium">Fabrication</th>
                  <th className="px-3 py-2 font-medium">Keywords</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {latest.metrics.cases.map((c) => {
                  const clean = c.fabrication_rate === 0 && !c.error;
                  return (
                    <tr key={c.case_id} className="border-b border-slate-100">
                      <td className="px-3 py-2 font-medium text-slate-900">
                        {c.case_id}
                      </td>
                      <td className="px-3 py-2 text-slate-500">{c.doc_type}</td>
                      <td className="px-3 py-2 text-emerald-600" style={num}>
                        {pct(c.grounding_rate)}
                      </td>
                      <td
                        className={cn(
                          "px-3 py-2",
                          c.fabrication_rate > 0
                            ? "text-red-600"
                            : "text-slate-600"
                        )}
                        style={num}
                      >
                        {pct(c.fabrication_rate)}
                        {c.leaked_claims.length > 0 && (
                          <span className="ml-1 text-xs">
                            ({c.leaked_claims.join(", ")})
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-600" style={num}>
                        {pct(c.keyword_coverage)}
                      </td>
                      <td className="px-3 py-2">
                        {clean ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-600">
                            <CheckCircle2 className="h-3 w-3" /> clean
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600">
                            <AlertTriangle className="h-3 w-3" />
                            {c.error ? "error" : "fabrication"}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
