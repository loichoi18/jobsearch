"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PdfPreview } from "@/components/jobs/pdf-preview";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  DocType,
  DocumentRow,
  DraftDocument,
  GroundingReport,
} from "@/lib/types";

const POLL_MS = 3000;
const DOC_LABEL: Record<DocType, string> = {
  cv: "CV",
  cover_letter: "Cover letter",
};

function parseDraft(row: DocumentRow): DraftDocument | null {
  if (!row.typst_source) return null;
  try {
    return JSON.parse(row.typst_source) as DraftDocument;
  } catch {
    return null;
  }
}

function GroundingPanel({ report }: { report: GroundingReport }) {
  const pct = Math.round(report.grounding_rate * 100);
  return (
    <div className="rounded-md border p-4">
      <div className="mb-3 flex items-baseline gap-3">
        <span className="gradient-text tnum text-4xl font-bold">
          {pct}%
        </span>
        <span className="text-sm font-medium">claim-grounding rate</span>
        <span className="text-xs text-muted-foreground">
          ({report.claims.filter((c) => c.verdict === "grounded").length}/
          {report.claims.length} claims traceable to your profile)
        </span>
      </div>

      <ul className="space-y-1.5">
        {report.claims.map((c, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <span
              className={cn(
                "mt-0.5 shrink-0 font-bold",
                c.verdict === "grounded" ? "text-emerald-600" : "text-red-600"
              )}
              aria-label={c.verdict}
            >
              {c.verdict === "grounded" ? "✓" : "✕"}
            </span>
            <span
              className={cn(
                c.verdict === "unsupported" &&
                  "text-red-700 line-through decoration-red-400"
              )}
            >
              {c.claim}
              {c.note && c.verdict === "unsupported" && (
                <span className="ml-1 text-xs text-muted-foreground no-underline">
                  — {c.note}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>

      {report.removed_claims.length > 0 && (
        <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
          {report.removed_claims.length} unsupported claim
          {report.removed_claims.length > 1 ? "s were" : " was"} removed from
          the final document — they could not be traced to your profile.
        </p>
      )}
    </div>
  );
}

function DocumentViewer({ row }: { row: DocumentRow }) {
  const draft = parseDraft(row);
  return (
    <div className="space-y-4">
      {row.pdf_path && <PdfPreview docId={row.id} />}
      {draft ? (
        <div className="space-y-4 rounded-md border bg-muted/30 p-4">
          {draft.sections.map((section) => (
            <div key={section.title}>
              {draft.doc_type === "cv" && (
                <h4 className="mb-1 text-sm font-semibold uppercase tracking-wide">
                  {section.title}
                </h4>
              )}
              <div className="space-y-2">
                {section.units.map((u, i) =>
                  draft.doc_type === "cv" ? (
                    <p key={i} className="text-sm">
                      • {u.text}
                    </p>
                  ) : (
                    <p key={i} className="text-sm leading-relaxed">
                      {u.text}
                    </p>
                  )
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No content stored.</p>
      )}
      {row.grounding_report && <GroundingPanel report={row.grounding_report} />}
    </div>
  );
}

export function DocumentsPanel({ jobId }: { jobId: string }) {
  const [docs, setDocs] = useState<DocumentRow[]>([]);
  const [selected, setSelected] = useState<DocumentRow | null>(null);
  const [generating, setGenerating] = useState<DocType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshList = useCallback(async () => {
    const res = await apiFetch(`/api/jobs/${jobId}/documents`);
    if (res.ok) setDocs(await res.json());
  }, [jobId]);

  useEffect(() => {
    void refreshList();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [refreshList]);

  const openDocument = useCallback(async (docId: string) => {
    const res = await apiFetch(`/api/documents/${docId}`);
    if (res.ok) setSelected(await res.json());
  }, []);

  async function generate(docType: DocType) {
    setGenerating(docType);
    setError(null);
    const res = await apiFetch(`/api/jobs/${jobId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_type: docType }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      setError(
        typeof body?.detail === "string"
          ? body.detail
          : "Generation failed to start."
      );
      setGenerating(null);
      return;
    }
    const { document_id } = await res.json();

    pollRef.current = setInterval(async () => {
      const poll = await apiFetch(`/api/documents/${document_id}`);
      if (!poll.ok) return;
      const row: DocumentRow = await poll.json();
      if (row.status === "pending") return;
      if (pollRef.current) clearInterval(pollRef.current);
      setGenerating(null);
      if (row.status === "failed") {
        setError(row.error ?? "Generation failed — try again.");
      } else {
        setSelected(row);
      }
      void refreshList();
    }, POLL_MS);
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle>Documents</CardTitle>
          <CardDescription>
            Drafter → Reviewer → Grounding verifier. Unsupported claims are
            removed, never sent.
          </CardDescription>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button
            size="sm"
            onClick={() => generate("cv")}
            disabled={generating !== null}
          >
            {generating === "cv" ? "Generating…" : "Generate CV"}
          </Button>
          <Button
            size="sm"
            onClick={() => generate("cover_letter")}
            disabled={generating !== null}
          >
            {generating === "cover_letter"
              ? "Generating…"
              : "Generate cover letter"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {generating && (
          <p className="text-sm text-muted-foreground">
            Drafting, reviewing, and verifying against your profile — this
            takes 30–60 seconds on the free tier…
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {docs.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {docs.map((d) => (
              <button
                key={d.id}
                onClick={() => void openDocument(d.id)}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-xs font-medium hover:bg-accent",
                  selected?.id === d.id && "border-primary bg-accent",
                  d.status === "failed" && "opacity-50"
                )}
              >
                {DOC_LABEL[d.doc_type]} v{d.version}
                {d.status === "pending" && " ⏳"}
                {d.status === "failed" && " ✕"}
                {d.grounding_report &&
                  ` · ${Math.round(d.grounding_report.grounding_rate * 100)}%`}
              </button>
            ))}
          </div>
        )}

        {selected ? (
          <DocumentViewer row={selected} />
        ) : (
          docs.length === 0 &&
          !generating && (
            <p className="text-sm text-muted-foreground">
              Nothing generated yet. PDF rendering lands in Prompt 7 — for now
              you get the structured content plus the grounding report.
            </p>
          )
        )}
      </CardContent>
    </Card>
  );
}
