"use client";

import { useCallback, useEffect, useState } from "react";

import { ProfileForm } from "@/components/profile/profile-form";
import { UploadPanel } from "@/components/profile/upload-panel";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { emptyProfile, type Profile } from "@/lib/types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadProfile = useCallback(async () => {
    const res = await apiFetch("/api/profile");
    if (res.ok) {
      const body = await res.json();
      setProfile(body.structured as Profile);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  async function handleResponse(res: Response, successMessage: string) {
    if (res.ok) {
      const body = await res.json();
      setProfile(body.structured as Profile);
      setMessage(successMessage);
    } else {
      const detail = await res
        .json()
        .then((b) => b.detail ?? res.statusText)
        .catch(() => res.statusText);
      setMessage(`Error: ${detail}`);
    }
  }

  async function uploadPdf(file: File) {
    setBusy(true);
    setMessage(null);
    const form = new FormData();
    form.append("file", file);
    const res = await apiFetch("/api/profile/upload", {
      method: "POST",
      body: form,
    });
    await handleResponse(res, "Profile extracted from PDF. Review and save.");
    setBusy(false);
  }

  async function submitText(text: string) {
    setBusy(true);
    setMessage(null);
    const res = await apiFetch("/api/profile/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    await handleResponse(res, "Profile extracted from text. Review and save.");
    setBusy(false);
  }

  function startManual() {
    setMessage("Enter your details below, then Save.");
    setProfile(emptyProfile);
  }

  async function saveProfile(p: Profile) {
    setSaving(true);
    setMessage(null);
    const res = await apiFetch("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    });
    await handleResponse(res, "Profile saved.");
    setSaving(false);
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Profile</h2>
        <p className="text-muted-foreground">
          Upload your CV to auto-extract a structured profile, or enter your
          details manually. Either way you can edit everything, and nothing is
          ever invented: empty fields stay empty.
        </p>
      </div>

      <UploadPanel onUploadPdf={uploadPdf} onSubmitText={submitText} busy={busy} />

      {message && (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {message}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading profile…</p>
      ) : profile ? (
        <ProfileForm value={profile} onSave={saveProfile} saving={saving} />
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            No profile yet — upload a CV or paste text above, or enter your
            details by hand.
          </p>
          <Button variant="outline" onClick={startManual}>
            Enter details manually
          </Button>
        </div>
      )}
    </div>
  );
}
