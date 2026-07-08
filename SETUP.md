# JobPilot AU — Setup Guide

From a fresh clone to a running app. Target: **under 15 minutes**.

There are three moving parts: **Supabase** (database + auth + storage),
**Render** (FastAPI backend), and **Vercel** (Next.js frontend). Do them in
that order — the frontend and backend both need Supabase keys.

---

## 1. Supabase (database, auth, storage)

1. Create a project at [supabase.com](https://supabase.com) → **New project**.
   Pick a region close to your users (Sydney/Singapore for AU). Save the
   database password.
2. **Run the migrations.** Dashboard → **SQL Editor** → **New query**. Paste and
   run each file from `supabase/migrations/` **in order**:
   - `0001_init.sql` (tables, pgvector extension, RLS policies)
   - `0002_retrieval.sql` (dense + sparse retrieval RPCs)
   - `0003_documents_status.sql`
   - `0004_jobs_tracking.sql`
3. **Create the storage bucket.** Dashboard → **Storage** → **New bucket** →
   name it exactly `documents`, and keep it **private** (do not make it public —
   PDFs are served through short-lived signed URLs).
4. **Enable Google OAuth** (optional but recommended). Dashboard →
   **Authentication → Providers → Google** → enable, and paste a Google OAuth
   client ID/secret from the
   [Google Cloud console](https://console.cloud.google.com/apis/credentials).
   Add the Supabase callback URL it shows you to the Google client's authorized
   redirect URIs.
5. **Copy your keys.** Dashboard → **Project Settings → API**:
   - `Project URL` → `SUPABASE_URL` (backend) and `NEXT_PUBLIC_SUPABASE_URL` (frontend)
   - `service_role` key → `SUPABASE_SERVICE_KEY` (backend only — **never** ship to the frontend)
   - `anon` key → `NEXT_PUBLIC_SUPABASE_ANON_KEY` (frontend)
   - `JWT Secret` → `SUPABASE_JWT_SECRET` (backend — verifies user tokens)

## 2. Get the other API keys

- **Gemini** (free): [Google AI Studio](https://aistudio.google.com/apikey) →
  create an API key → `GEMINI_API_KEY`.
- **Adzuna** (free): [developer.adzuna.com](https://developer.adzuna.com) →
  register → `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.

## 3. Run locally

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # fill in the keys from steps 1–2
uvicorn main:app --reload --port 8000
```

Install Typst so PDF rendering works locally: download from the
[Typst releases](https://github.com/typst/typst/releases) (or
`brew install typst` / `winget install typst`) and keep `TYPST_BIN=typst`.

```bash
# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local           # fill in the NEXT_PUBLIC_* keys
npm run dev                          # http://localhost:3000
```

Sign in, upload your CV on **/profile**, search or paste a job on **/jobs**,
and generate documents.

## 4. Deploy the backend (Render)

1. Push the repo to GitHub.
2. Render → **New → Blueprint** → select the repo. Render reads `render.yaml`.
3. Set the secret env vars it prompts for (everything marked `sync: false`):
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`,
   `GEMINI_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, and `FRONTEND_URL`
   (your Vercel URL from step 5 — you can set it after the frontend deploys).
4. Deploy. `build.sh` downloads the Typst binary; the health check hits
   `/api/health`. **Free tier sleeps after ~15 min idle** and cold-starts in
   ~50s — expected, not a bug.

## 5. Deploy the frontend (Vercel)

1. Vercel → **New Project** → import the repo → set **Root Directory** to
   `frontend`.
2. Environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL` → your Render URL (e.g. `https://jobpilot-au-api.onrender.com`)
3. Deploy, then copy the Vercel URL back into Render's `FRONTEND_URL` (CORS) and
   redeploy the backend.
4. **Auth redirect URLs.** Supabase → **Authentication → URL Configuration**:
   set **Site URL** to your Vercel URL and add
   `https://YOUR-APP.vercel.app/auth/callback` to **Redirect URLs** (and
   `http://localhost:3000/auth/callback` for local dev).

## 6. Run the evaluation harness (optional, recommended)

```bash
cd backend
# Free, deterministic — no API keys, no cost:
python -m evaluation.harness --dataset v1 --mock
# Real run against Gemini, persisted so the /evals page shows it:
python -m evaluation.harness --dataset v1 --cases 5 --persist
```

The `/evals` page reads persisted runs from the `eval_runs` table.

---

### Troubleshooting

- **401 on API calls**: `SUPABASE_JWT_SECRET` on the backend must match the
  project's JWT secret exactly.
- **CORS errors**: `FRONTEND_URL` on Render must equal your Vercel origin
  (no trailing slash).
- **PDF never appears**: confirm the `documents` bucket exists and is private,
  and that `TYPST_BIN` resolves (locally `typst`, on Render `./bin/typst`).
- **429 Too Many Requests**: the generation endpoint is rate-limited to 10/hour
  per user on the free demo tier.
