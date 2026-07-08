"""Dense retrieval: pgvector cosine similarity via the match_profile_chunks RPC."""

from retrieval.schemas import ChunkSearchRepo, RetrievedChunk


class DenseSearcher:
    def __init__(self, repo: ChunkSearchRepo) -> None:
        self._repo = repo

    def search(
        self, query_embedding: list[float], user_id: str, count: int
    ) -> list[RetrievedChunk]:
        rows = self._repo.dense_search(query_embedding, user_id, count)
        return [
            RetrievedChunk(
                id=str(row["id"]),
                section=row["section"],
                content=row["content"],
                metadata=row.get("metadata") or {},
                score=float(row["similarity"]),
            )
            for row in rows
        ]
