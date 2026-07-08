"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

/** "Paste a job" intake: title + company + URL and/or JD text. */
export function PasteJobDialog({ open, onClose, onSaved }: Props) {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function submit() {
    setSaving(true);
    setError(null);
    const res = await apiFetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: "manual",
        title,
        company: company || null,
        url: url || null,
        description: description || null,
      }),
    });
    setSaving(false);
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      const detail = body?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Please provide a title and either a URL or the job description text."
      );
      return;
    }
    setTitle("");
    setCompany("");
    setUrl("");
    setDescription("");
    onSaved();
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-lg border bg-background p-6 shadow-lg">
        <h3 className="text-lg font-semibold">Paste a job</h3>
        <p className="mb-4 text-sm text-muted-foreground">
          For Seek/LinkedIn/GradConnection postings, paste the job description
          text — we never scrape those sites.
        </p>
        <div className="space-y-3">
          <div>
            <Label htmlFor="pj-title">Job title *</Label>
            <Input
              id="pj-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Machine Learning Intern"
            />
          </div>
          <div>
            <Label htmlFor="pj-company">Company</Label>
            <Input
              id="pj-company"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="pj-url">URL (optional)</Label>
            <Input
              id="pj-url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
            />
          </div>
          <div>
            <Label htmlFor="pj-desc">Job description</Label>
            <Textarea
              id="pj-desc"
              rows={8}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Paste the full JD text here…"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button
              onClick={submit}
              disabled={saving || !title || (!url && !description)}
            >
              {saving ? "Saving…" : "Save job"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
