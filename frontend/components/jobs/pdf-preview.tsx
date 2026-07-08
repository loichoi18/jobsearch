"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

/** Fetches a short-lived signed URL and shows the PDF inline + download. */
export function PdfPreview({ docId }: { docId: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setUrl(null);
    setFailed(false);
    (async () => {
      const res = await apiFetch(`/api/documents/${docId}/pdf`);
      if (cancelled) return;
      if (res.ok) {
        const body = await res.json();
        setUrl(body.url);
      } else {
        setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docId]);

  if (failed) {
    return (
      <p className="text-sm text-muted-foreground">
        No PDF available for this version (rendering may have failed — the
        content and grounding report above are still valid).
      </p>
    );
  }
  if (!url) {
    return <p className="text-sm text-muted-foreground">Loading PDF…</p>;
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <Button size="sm" variant="outline" asChild>
          <a href={url} target="_blank" rel="noreferrer" download>
            Download PDF
          </a>
        </Button>
      </div>
      <iframe
        src={url}
        title="Document PDF preview"
        className="h-[560px] w-full rounded-md border"
      />
    </div>
  );
}
