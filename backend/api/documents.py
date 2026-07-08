"""Document generation endpoints. Routers hold no business logic (CLAUDE.md)."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from api.deps import CurrentUserId
from api.rate_limit import GENERATION_RATE_LIMIT, limiter
from configs.settings import get_settings
from generation.doc_schemas import DocType, DocumentStatus
from generation.pipeline import GenerationPipeline
from generation.provider import get_provider
from generation.renderer import DocumentRenderer
from retrieval.dense import DenseSearcher
from retrieval.hybrid import HybridRetriever
from retrieval.sparse import SparseSearcher
from services.generation_service import GenerationService, NoProfileError
from services.jobs_service import JobNotFoundError
from storage.pdf_storage import PdfStorage
from storage.repositories import (
    ChunkRepository,
    DocumentRepository,
    JobRepository,
    ProfileRepository,
)
from storage.supabase_client import get_supabase

router = APIRouter(prefix="/api", tags=["documents"])


def get_generation_service() -> GenerationService:
    settings = get_settings()
    client = get_supabase()
    provider = get_provider()
    chunk_repo = ChunkRepository(client)
    pipeline = GenerationPipeline(
        provider=provider,
        retriever=HybridRetriever(
            provider=provider,
            dense=DenseSearcher(chunk_repo),
            sparse=SparseSearcher(chunk_repo),
        ),
    )
    return GenerationService(
        pipeline=pipeline,
        doc_repo=DocumentRepository(client),
        job_repo=JobRepository(client),
        profile_repo=ProfileRepository(client),
        renderer=DocumentRenderer(settings.typst_bin),
        pdf_storage=PdfStorage(client),
        signed_url_ttl_s=settings.signed_url_ttl_s,
    )


ServiceDep = Depends(get_generation_service)


class GenerateRequest(BaseModel):
    doc_type: DocType


class GenerateResponse(BaseModel):
    document_id: str
    doc_type: DocType
    version: int
    status: DocumentStatus


class PdfUrlResponse(BaseModel):
    url: str


@router.post(
    "/jobs/{job_id}/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(GENERATION_RATE_LIMIT)
async def generate_document(
    request: Request,
    job_id: str,
    body: GenerateRequest,
    user_id: CurrentUserId,
    background_tasks: BackgroundTasks,
    service: GenerationService = ServiceDep,
) -> GenerateResponse:
    try:
        row = service.start_generation(user_id, job_id, body.doc_type)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from exc
    except NoProfileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    background_tasks.add_task(
        service.run_generation, user_id, job_id, row["id"], body.doc_type
    )
    return GenerateResponse(
        document_id=row["id"],
        doc_type=body.doc_type,
        version=row["version"],
        status=row["status"],
    )


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    user_id: CurrentUserId,
    service: GenerationService = ServiceDep,
) -> dict[str, Any]:
    row = service.get_document(user_id, doc_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return row


@router.get("/documents/{doc_id}/pdf", response_model=PdfUrlResponse)
async def get_document_pdf(
    doc_id: str,
    user_id: CurrentUserId,
    service: GenerationService = ServiceDep,
) -> PdfUrlResponse:
    url = service.get_pdf_url(user_id, doc_id)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No PDF for this document (rendering may have failed).",
        )
    return PdfUrlResponse(url=url)


@router.get("/jobs/{job_id}/documents")
async def list_documents(
    job_id: str,
    user_id: CurrentUserId,
    service: GenerationService = ServiceDep,
) -> list[dict[str, Any]]:
    return service.list_documents(user_id, job_id)
