-- Prompt 6: generation is a long-running background task; documents need a
-- pollable status plus an error message for failed runs.

alter table public.documents
    add column status text not null default 'complete'
        check (status in ('pending', 'complete', 'failed')),
    add column error text;

create index documents_job_type_idx
    on public.documents (job_id, doc_type, version desc);
