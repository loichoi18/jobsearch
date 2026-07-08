"""Profile orchestration: parse -> extract -> persist -> re-index for RAG."""

from typing import Any

from generation.provider import LLMProvider
from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.profile_extractor import extract_profile
from ingestion.profile_schema import Profile
from services.indexing_service import ProfileIndexer
from storage.repositories import ProfileRepositoryProtocol


class ProfileService:
    def __init__(
        self,
        repo: ProfileRepositoryProtocol,
        provider: LLMProvider,
        indexer: ProfileIndexer | None = None,
    ) -> None:
        self._repo = repo
        self._provider = provider
        self._indexer = indexer

    async def ingest_pdf(self, user_id: str, pdf_bytes: bytes) -> Profile:
        raw_text = extract_text_from_pdf(pdf_bytes)
        return await self._ingest_text(user_id, raw_text)

    async def ingest_text(self, user_id: str, raw_text: str) -> Profile:
        return await self._ingest_text(user_id, raw_text)

    async def _ingest_text(self, user_id: str, raw_text: str) -> Profile:
        profile = await extract_profile(raw_text, self._provider)
        self._repo.upsert(user_id, profile.model_dump(), raw_text)
        await self._reindex(user_id, profile)
        return profile

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        return self._repo.get(user_id)

    async def update_profile(self, user_id: str, structured: Profile) -> Profile:
        """Manual edits from the frontend form (already schema-validated)."""
        self._repo.upsert(user_id, structured.model_dump())
        await self._reindex(user_id, structured)
        return structured

    async def _reindex(self, user_id: str, profile: Profile) -> None:
        if self._indexer is not None:
            await self._indexer.reindex(user_id, profile)
