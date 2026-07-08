"""Profile indexing: chunk -> embed (one batched call) -> replace in DB.

Runs on every profile save/update so retrieval always reflects the latest
profile. replace_chunks is delete-then-insert, making re-indexing idempotent.
"""

from generation.provider import LLMProvider
from ingestion.chunker import chunk_profile
from ingestion.profile_schema import Profile
from storage.repositories import ChunkRepositoryProtocol


class ProfileIndexer:
    def __init__(
        self, chunk_repo: ChunkRepositoryProtocol, provider: LLMProvider
    ) -> None:
        self._chunk_repo = chunk_repo
        self._provider = provider

    async def reindex(self, user_id: str, profile: Profile) -> int:
        """Re-chunk and re-embed the profile. Returns the chunk count."""
        chunks = chunk_profile(profile)
        if not chunks:
            self._chunk_repo.replace_chunks(user_id, [])
            return 0

        embeddings = await self._provider.embed([c.content for c in chunks])

        rows = [
            {
                "user_id": user_id,
                "section": chunk.section,
                "content": chunk.content,
                "embedding": embedding,
                "metadata": chunk.metadata,
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        return self._chunk_repo.replace_chunks(user_id, rows)
