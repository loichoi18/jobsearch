"""Shared retrieval types."""

from typing import Any, Protocol

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    id: str
    section: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float


class ChunkSearchRepo(Protocol):
    """What retrieval needs from storage; enables in-memory fakes in tests."""

    def dense_search(
        self, query_embedding: list[float], user_id: str, count: int
    ) -> list[dict[str, Any]]: ...

    def sparse_search(
        self, query_text: str, user_id: str, count: int
    ) -> list[dict[str, Any]]: ...
