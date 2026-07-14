"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function EnhancePage() {
  const { t } = useI18n();
  const [companyName, setCompanyName] = useState("");
  const [resume, setResume] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const canSubmit =
    companyName.trim() && resume.trim() && jobDescription.trim() && !loading;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!companyName.trim() || !resume.trim() || !jobDescription.trim()) {
      setError(t("enhance.required"));
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setCopied(false);
    try {
      const res = await apiFetch("/api/enhance/cv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: companyName,
          resume,
          job_description: jobDescription,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? t("enhance.error"));
      }
      const data = (await res.json()) as { result: string };
      setResult(data.result);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("enhance.error"));
    } finally {
      setLoading(false);
    }
  }

  async function copyResult() {
    if (!result) return;
    await navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {t("enhance.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("enhance.subtitle")}
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="company">{t("enhance.companyLabel")}</Label>
              <Input
                id="company"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder={t("enhance.companyPlaceholder")}
                maxLength={200}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="resume">{t("enhance.resumeLabel")}</Label>
              <Textarea
                id="resume"
                value={resume}
                onChange={(e) => setResume(e.target.value)}
                placeholder={t("enhance.resumePlaceholder")}
                className="min-h-[180px]"
                maxLength={40000}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="jd">{t("enhance.jdLabel")}</Label>
              <Textarea
                id="jd"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder={t("enhance.jdPlaceholder")}
                className="min-h-[180px]"
                maxLength={40000}
              />
            </div>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" disabled={!canSubmit}>
              {loading ? t("enhance.submitting") : t("enhance.submit")}
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>{t("enhance.resultTitle")}</CardTitle>
              <CardDescription className="mt-1">
                {companyName}
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={copyResult}>
              {copied ? t("enhance.copied") : t("enhance.copy")}
            </Button>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-foreground">
              {result}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
