"""Profile endpoints. Routers hold no business logic (CLAUDE.md)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from api.deps import CurrentUserId
from generation.provider import get_provider
from ingestion.pdf_parser import PdfParseError
from ingestion.profile_extractor import ProfileExtractionError
from ingestion.profile_schema import Profile
from services.indexing_service import ProfileIndexer
from services.profile_service import ProfileService
from storage.repositories import ChunkRepository, ProfileRepository
from storage.supabase_client import get_supabase

router = APIRouter(prefix="/api/profile", tags=["profile"])


def get_profile_service() -> ProfileService:
    client = get_supabase()
    provider = get_provider()
    return ProfileService(
        repo=ProfileRepository(client),
        provider=provider,
        indexer=ProfileIndexer(ChunkRepository(client), provider),
    )


ServiceDep = Depends(get_profile_service)


class TextIngestRequest(BaseModel):
    text: str = Field(min_length=50, description="Raw CV / LinkedIn text")


class ProfileResponse(BaseModel):
    structured: Profile
    raw_text: str | None = None


@router.post("/upload", response_model=ProfileResponse)
async def upload_profile_pdf(
    file: UploadFile,
    user_id: CurrentUserId,
    service: ProfileService = ServiceDep,
) -> ProfileResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload a PDF file.",
        )
    pdf_bytes = await file.read()
    try:
        profile = await service.ingest_pdf(user_id, pdf_bytes)
    except PdfParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except ProfileExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return ProfileResponse(structured=profile)


@router.post("/text", response_model=ProfileResponse)
async def ingest_profile_text(
    body: TextIngestRequest,
    user_id: CurrentUserId,
    service: ProfileService = ServiceDep,
) -> ProfileResponse:
    try:
        profile = await service.ingest_text(user_id, body.text)
    except ProfileExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return ProfileResponse(structured=profile)


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user_id: CurrentUserId,
    service: ProfileService = ServiceDep,
) -> ProfileResponse:
    row: dict[str, Any] | None = service.get_profile(user_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile yet — upload a CV first.",
        )
    return ProfileResponse(
        structured=Profile.model_validate(row["structured"]),
        raw_text=row.get("raw_text"),
    )


@router.put("", response_model=ProfileResponse)
async def update_profile(
    structured: Profile,
    user_id: CurrentUserId,
    service: ProfileService = ServiceDep,
) -> ProfileResponse:
    profile = await service.update_profile(user_id, structured)
    return ProfileResponse(structured=profile)
