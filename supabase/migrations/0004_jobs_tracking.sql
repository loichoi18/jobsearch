-- Prompt 8: application tracker needs applied_at (auto-set on move to
-- Applied) and updated_at (days-since-last-update on Kanban cards).

alter table public.jobs
    add column applied_at timestamptz,
    add column updated_at timestamptz not null default now();

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger jobs_set_updated_at
    before update on public.jobs
    for each row
    execute function public.set_updated_at();
