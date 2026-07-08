import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Render's free tier can cold-start (~50s), so allow a generous timeout before
// giving up — but DO give up, so the UI never spins forever.
const TIMEOUT_MS = 60_000;

/** Fetch against the FastAPI backend with the Supabase access token attached.
 * Rejects on network failure or after TIMEOUT_MS so callers can show an error
 * instead of hanging. */
export async function apiFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = new Headers(init.headers);
  if (session) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  return fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    signal: init.signal ?? AbortSignal.timeout(TIMEOUT_MS),
  });
}
