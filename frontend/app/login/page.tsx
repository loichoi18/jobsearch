"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function sendMagicLink(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/auth/callback` },
    });
    setBusy(false);
    if (error) setError(error.message);
    else setSent(true);
  }

  async function signInWithGoogle() {
    setError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
    if (error) setError(error.message);
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-slate-50 p-6">
      <span className="text-lg font-semibold tracking-tight">JobPilot AU</span>
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in to JobPilot AU</CardTitle>
          <CardDescription>
            Magic link by email, or continue with Google.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {sent ? (
            <p className="text-sm">
              Check your inbox — we sent a sign-in link to{" "}
              <span className="font-medium">{email}</span>.
            </p>
          ) : (
            <form onSubmit={sendMagicLink} className="space-y-3">
              <Input
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Button type="submit" className="w-full" disabled={busy}>
                {busy ? "Sending…" : "Send magic link"}
              </Button>
            </form>
          )}
          <Button
            variant="outline"
            className="w-full"
            onClick={signInWithGoogle}
          >
            Continue with Google
          </Button>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </main>
  );
}
