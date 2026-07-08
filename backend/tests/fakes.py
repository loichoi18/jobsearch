"""In-memory fakes shared across tests."""

from typing import Any

from generation.provider import LLMProvider


class FakeProvider(LLMProvider):
    """Returns queued responses in order; records every call."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        system: str,
        user: str,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        self.calls.append({"system": system, "user": user, "schema": json_schema})
        return self._responses.pop(0)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 768 for _ in texts]


class FakeJobRepo:
    """Dict-backed stand-in for JobRepository."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def insert(self, user_id: str, row: dict[str, Any]) -> dict[str, Any]:
        self._counter += 1
        job_id = f"00000000-0000-0000-0000-{self._counter:012d}"
        stored = {**row, "id": job_id, "user_id": user_id}
        self.rows[job_id] = stored
        return stored

    def list(
        self, user_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        rows = [r for r in self.rows.values() if r["user_id"] == user_id]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        return rows

    def get(self, user_id: str, job_id: str) -> dict[str, Any] | None:
        row = self.rows.get(job_id)
        return row if row and row["user_id"] == user_id else None

    def update(
        self, user_id: str, job_id: str, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        row = self.get(user_id, job_id)
        if row is None:
            return None
        row.update(fields)
        return row

    def delete(self, user_id: str, job_id: str) -> bool:
        if self.get(user_id, job_id) is None:
            return False
        del self.rows[job_id]
        return True


class FakeMatchingService:
    """No-op stand-in for MatchingService in job-intake tests."""

    def __init__(self) -> None:
        self.background_calls: list[tuple[str, str]] = []

    async def analyze_quietly(self, user_id: str, job_id: str) -> None:
        self.background_calls.append((user_id, job_id))


class FakeDocumentRepo:
    """Dict-backed stand-in for DocumentRepository."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def insert(self, user_id: str, row: dict[str, Any]) -> dict[str, Any]:
        self._counter += 1
        doc_id = f"d0000000-0000-0000-0000-{self._counter:012d}"
        stored = {**row, "id": doc_id, "user_id": user_id}
        self.rows[doc_id] = stored
        return stored

    def get(self, user_id: str, doc_id: str) -> dict[str, Any] | None:
        row = self.rows.get(doc_id)
        return row if row and row["user_id"] == user_id else None

    def update(
        self, user_id: str, doc_id: str, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        row = self.get(user_id, doc_id)
        if row is None:
            return None
        row.update(fields)
        return row

    def list_for_job(self, user_id: str, job_id: str) -> list[dict[str, Any]]:
        return [
            r
            for r in self.rows.values()
            if r["user_id"] == user_id and r["job_id"] == job_id
        ]

    def next_version(self, user_id: str, job_id: str, doc_type: str) -> int:
        versions = [
            int(r["version"])
            for r in self.rows.values()
            if r["user_id"] == user_id
            and r["job_id"] == job_id
            and r["doc_type"] == doc_type
        ]
        return max(versions, default=0) + 1


class FakeProfileRepo:
    """Dict-backed stand-in for ProfileRepository."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def get(self, user_id: str) -> dict[str, Any] | None:
        return self.rows.get(user_id)

    def upsert(
        self,
        user_id: str,
        structured: dict[str, Any],
        raw_text: str | None = None,
    ) -> dict[str, Any]:
        row = self.rows.setdefault(user_id, {"user_id": user_id})
        row["structured"] = structured
        if raw_text is not None:
            row["raw_text"] = raw_text
        return row
