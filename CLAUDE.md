# JobPilot AU — Project Constitution

## Mission
AI job-application copilot for the Australian graduate/internship market. Web app. Portfolio-grade quality: this will be reviewed by recruiters.

## Stack (fixed — do not substitute)
- Frontend: Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui. Deployed on Vercel.
- Backend: FastAPI, Python 3.11, Pydantic v2 for ALL configs and schemas. Deployed on Render free tier.
- DB: Supabase (Postgres + pgvector + Auth + Storage). Access via supabase-py on backend; frontend uses Supabase Auth client only.
- LLM: Google Gemini free tier (gemini-2.0-flash for generation, text-embedding-004 for embeddings) accessed ONLY through an LLMProvider abstraction in backend/generation/provider.py so it can be swapped for Claude later. Never call the Gemini SDK directly from business logic.
- Job data: Adzuna API (Australia) + manual paste of job description. NEVER scrape Seek or LinkedIn.
- PDF: Typst (binary, installed via build script). NOT LaTeX.

## Backend architecture (layered — mandatory)
backend/
  api/          # FastAPI routers only, no business logic
  services/     # orchestration
  ingestion/    # PDF parsing, profile extraction, chunking
  retrieval/    # hybrid retrieval: dense (pgvector) + sparse (Postgres FTS), fused with Reciprocal Rank Fusion
  generation/   # LLMProvider abstraction, drafter agent, reviewer agent, grounding verifier, Typst rendering
  evaluation/   # golden dataset, metrics, regression harness
  storage/      # supabase client, repositories
  configs/      # pydantic-settings, all env vars typed
  tests/        # pytest: unit + integration

## Engineering rules
1. Type hints everywhere. Pydantic models for every request/response and config.
2. Every component independently testable; write pytest tests alongside each feature.
3. Generation must answer ONLY from retrieved profile context. Every claim in generated documents must cite the profile chunk that supports it. Refuse/flag unsupported claims. Never fabricate skills, dates, or achievements.
4. All secrets via environment variables through pydantic-settings. Never hardcode keys.
5. Small modules. No file over ~300 lines. No monolithic scripts.
6. Before implementing any prompt task: state the architecture plan, files to be created, and interfaces FIRST, then implement, then write tests, then run them.

## Core domain concepts
- Profile: structured JSON (education, projects, skills, experience, certifications, visa_status) + chunked/embedded raw text in profile_chunks.
- Grounding report: for each generated document, a JSON list of {claim, supporting_chunk_ids, verdict: grounded|unsupported}. Grounding rate = grounded / total.
- Drafter-reviewer pipeline: Drafter writes with profile context + JD. Reviewer (separate call, fresh context) critiques against a rubric. Drafter revises once. Verifier produces the grounding report and strips unsupported claims.
- Relevance-weighted cutting: when CV exceeds 2 pages, score each bullet by (relevance to JD × uniqueness × cover-letter-dependency) and cut lowest-first, re-render, repeat.
