-- JobPilot AU — 0001_init.sql
-- Core schema: profiles, profile_chunks, jobs, documents, eval_runs
-- All user-owned tables have RLS with owner-only policies.

-- Extensions -----------------------------------------------------------------
create extension if not exists vector;

-- profiles -------------------------------------------------------------------
create table public.profiles (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null unique references auth.users (id) on delete cascade,
    structured  jsonb not null default '{}'::jsonb,
    raw_text    text,
    updated_at  timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles_owner_all"
    on public.profiles
    for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- profile_chunks ---------------------------------------------------------------
create table public.profile_chunks (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references auth.users (id) on delete cascade,
    section    text not null,
    content    text not null,
    embedding  vector(768),
    metadata   jsonb not null default '{}'::jsonb
);

alter table public.profile_chunks enable row level security;

create policy "profile_chunks_owner_all"
    on public.profile_chunks
    for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- Dense retrieval: cosine-distance ivfflat index
create index profile_chunks_embedding_idx
    on public.profile_chunks
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- Sparse retrieval: full-text search GIN index
create index profile_chunks_content_fts_idx
    on public.profile_chunks
    using gin (to_tsvector('english', content));

-- jobs -------------------------------------------------------------------------
create table public.jobs (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references auth.users (id) on delete cascade,
    source       text not null check (source in ('adzuna', 'manual')),
    title        text not null,
    company      text,
    location     text,
    description  text,
    url          text,
    salary_min   numeric,
    salary_max   numeric,
    status       text not null default 'saved'
                 check (status in ('saved', 'applied', 'interview', 'offer', 'rejected')),
    match_score  numeric,
    skill_gaps   jsonb,
    created_at   timestamptz not null default now()
);

alter table public.jobs enable row level security;

create policy "jobs_owner_all"
    on public.jobs
    for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create index jobs_user_status_idx on public.jobs (user_id, status);

-- documents ----------------------------------------------------------------------
create table public.documents (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid not null references auth.users (id) on delete cascade,
    job_id            uuid not null references public.jobs (id) on delete cascade,
    doc_type          text not null check (doc_type in ('cv', 'cover_letter')),
    version           int not null default 1,
    typst_source      text,
    pdf_path          text,
    grounding_report  jsonb,
    created_at        timestamptz not null default now()
);

alter table public.documents enable row level security;

create policy "documents_owner_all"
    on public.documents
    for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create index documents_job_idx on public.documents (job_id, doc_type, version);

-- eval_runs ------------------------------------------------------------------------
-- Not user-owned: written by the evaluation harness (service role),
-- readable by any signed-in user (the /evals page is a public demo surface).
create table public.eval_runs (
    id               uuid primary key default gen_random_uuid(),
    dataset_version  text not null,
    metrics          jsonb not null default '{}'::jsonb,
    created_at       timestamptz not null default now()
);

alter table public.eval_runs enable row level security;

create policy "eval_runs_read_authenticated"
    on public.eval_runs
    for select
    to authenticated
    using (true);
