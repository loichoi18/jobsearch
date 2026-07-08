"""Sparse retrieval: Postgres full-text search via the search_profile_chunks_fts RPC."""

from retrieval.schemas import ChunkSearchRepo, RetrievedChunk


class SparseSearcher:
    def __init__(self, repo: ChunkSearchRepo) -> None:
        self._repo = repo

    def search(
        self, query_text: str, user_id: str, count: int
    ) -> list[RetrievedChunk]:
        rows = self._repo.sparse_search(query_text, user_id, count)
        return [
            RetrievedChunk(
                id=str(row["id"]),
                section=row["section"],
                content=row["content"],
                metadata=row.get("metadata") or {},
                score=float(row["rank"]),
            )
            for row in rows
        ]
