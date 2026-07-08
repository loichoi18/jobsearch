"""Data-access repositories. Only this module talks to Supabase tables/RPCs."""

import json
from datetime import datetime, timezone
from typing import Any, Protocol

from supabase import Client


class ProfileRepositoryProtocol(Protocol):
    """Interface used by services; enables in-memory fakes in tests."""

    def get(self, user_id: str) -> dict[str, Any] | None: ...

    def upsert(
        self,
        user_id: str,
        structured: dict[str, Any],
        raw_text: str | None = None,
    ) -> dict[str, Any]: ...


class ChunkRepositoryProtocol(Protocol):
    """Chunk persistence + search interface (dense/sparse via SQL RPCs)."""

    def replace_chunks(
        self, user_id: str, rows: list[dict[str, Any]]
    ) -> int: ...

    def dense_search(
        self, query_embedding: list[float], user_id: str, count: int
    ) -> list[dict[str, Any]]: ...

    def sparse_search(
        self, query_text: str, user_id: str, count: int
    ) -> list[dict[str, Any]]: ...


class JobRepositoryProtocol(Protocol):
    """Job persistence interface; enables in-memory fakes in tests."""

    def insert(self, user_id: str, row: dict[str, Any]) -> dict[str, Any]: ...

    def list(
        self, user_id: str, status: str | None = None
    ) -> list[dict[str, Any]]: ...

    def get(self, user_id: str, job_id: str) -> dict[str, Any] | None: ...

    def update(
        self, user_id: str, job_id: str, fields: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    def delete(self, user_id: str, job_id: str) -> bool: ...


class DocumentRepositoryProtocol(Protocol):
    """Document persistence interface; enables in-memory fakes in tests."""

    def insert(self, user_id: str, row: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, user_id: str, doc_id: str) -> dict[str, Any] | None: ...

    def update(
        self, user_id: str, doc_id: str, fields: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    def list_for_job(
        self, user_id: str, job_id: str
    ) -> list[dict[str, Any]]: ...

    def next_version(
        self, user_id: str, job_id: str, doc_type: str
    ) -> int: ...


class ProfileRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def get(self, user_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def upsert(
        self,
        user_id: str,
        structured: dict[str, Any],
        raw_text: str | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "user_id": user_id,
            "structured": structured,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if raw_text is not None:
            row["raw_text"] = raw_text
        result = (
            self._client.table("profiles")
            .upsert(row, on_conflict="user_id")
            .execute()
        )
        return result.data[0]


class ChunkRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def replace_chunks(self, user_id: str, rows: list[dict[str, Any]]) -> int:
        """Idempotent re-index: delete this user's chunks, then insert fresh."""
        self._client.table("profile_chunks").delete().eq(
            "user_id", user_id
        ).execute()
        if not rows:
            return 0
        result = self._client.table("profile_chunks").insert(rows).execute()
        return len(result.data)

    def dense_search(
        self, query_embedding: list[float], user_id: str, count: int
    ) -> list[dict[str, Any]]:
        result = self._client.rpc(
            "match_profile_chunks",
            {
                "query_embedding": query_embedding,
                "match_user_id": user_id,
                "match_count": count,
            },
        ).execute()
        return result.data or []

    def sparse_search(
        self, query_text: str, user_id: str, count: int
    ) -> list[dict[str, Any]]:
        result = self._client.rpc(
            "search_profile_chunks_fts",
            {
                "query_text": query_text,
                "match_user_id": user_id,
                "match_count": count,
            },
        ).execute()
        return result.data or []

    def list_embeddings(self, user_id: str) -> list[list[float]]:
        """All of this user's chunk embeddings (for mean-profile similarity).

        pgvector columns come back from PostgREST as strings like
        "[0.1,0.2,...]" — parse them into float lists.
        """
        result = (
            self._client.table("profile_chunks")
            .select("embedding")
            .eq("user_id", user_id)
            .execute()
        )
        embeddings: list[list[float]] = []
        for row in result.data or []:
            value = row.get("embedding")
            if value is None:
                continue
            if isinstance(value, str):
                value = json.loads(value)
            embeddings.append([float(x) for x in value])
        return embeddings


class JobRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def insert(self, user_id: str, row: dict[str, Any]) -> dict[str, Any]:
        payload = {**row, "user_id": user_id}
        result = self._client.table("jobs").insert(payload).execute()
        return result.data[0]

    def list(
        self, user_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        query = (
            self._client.table("jobs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if status:
            query = query.eq("status", status)
        return query.execute().data or []

    def get(self, user_id: str, job_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("jobs")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def update(
        self, user_id: str, job_id: str, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        result = (
            self._client.table("jobs")
            .update(fields)
            .eq("user_id", user_id)
            .eq("id", job_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete(self, user_id: str, job_id: str) -> bool:
        result = (
            self._client.table("jobs")
            .delete()
            .eq("user_id", user_id)
            .eq("id", job_id)
            .execute()
        )
        return bool(result.data)


class DocumentRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def insert(self, user_id: str, row: dict[str, Any]) -> dict[str, Any]:
        payload = {**row, "user_id": user_id}
        result = self._client.table("documents").insert(payload).execute()
        return result.data[0]

    def get(self, user_id: str, doc_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("documents")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", doc_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def update(
        self, user_id: str, doc_id: str, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        result = (
            self._client.table("documents")
            .update(fields)
            .eq("user_id", user_id)
            .eq("id", doc_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def list_for_job(self, user_id: str, job_id: str) -> list[dict[str, Any]]:
        result = (
            self._client.table("documents")
            .select("id, doc_type, version, status, created_at, grounding_report")
            .eq("user_id", user_id)
            .eq("job_id", job_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def next_version(self, user_id: str, job_id: str, doc_type: str) -> int:
        result = (
            self._client.table("documents")
            .select("version")
            .eq("user_id", user_id)
            .eq("job_id", job_id)
            .eq("doc_type", doc_type)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return 1
        return int(result.data[0]["version"]) + 1


class EvalRunRepository:
    """eval_runs is global (no user_id): the /evals page is a public demo view
    of the harness's own runs, read with the service key."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def insert(
        self, dataset_version: str, metrics: dict[str, Any]
    ) -> dict[str, Any]:
        result = (
            self._client.table("eval_runs")
            .insert({"dataset_version": dataset_version, "metrics": metrics})
            .execute()
        )
        return result.data[0]

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        result = (
            self._client.table("eval_runs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def get(self, run_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("eval_runs")
            .select("*")
            .eq("id", run_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
