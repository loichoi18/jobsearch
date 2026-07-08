-- JobPilot AU — 0002_retrieval.sql
-- RPC functions for dense (pgvector cosine) and sparse (Postgres FTS) retrieval.
-- Called by the backend with the service role; user scoping is explicit via
-- match_user_id so results never cross users.

create or replace function match_profile_chunks(
    query_embedding vector(768),
    match_user_id uuid,
    match_count int default 8
)
returns table (
    id uuid,
    section text,
    content text,
    metadata jsonb,
    similarity double precision
)
language sql
stable
as $$
    select
        pc.id,
        pc.section,
        pc.content,
        pc.metadata,
        1 - (pc.embedding <=> query_embedding) as similarity
    from public.profile_chunks pc
    where pc.user_id = match_user_id
      and pc.embedding is not null
    order by pc.embedding <=> query_embedding
    limit match_count;
$$;

create or replace function search_profile_chunks_fts(
    query_text text,
    match_user_id uuid,
    match_count int default 8
)
returns table (
    id uuid,
    section text,
    content text,
    metadata jsonb,
    rank double precision
)
language sql
stable
as $$
    select
        pc.id,
        pc.section,
        pc.content,
        pc.metadata,
        ts_rank(
            to_tsvector('english', pc.content),
            plainto_tsquery('english', query_text)
        )::double precision as rank
    from public.profile_chunks pc
    where pc.user_id = match_user_id
      and to_tsvector('english', pc.content) @@ plainto_tsquery('english', query_text)
    order by rank desc
    limit match_count;
$$;
