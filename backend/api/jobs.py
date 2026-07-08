"""Job endpoints. Routers hold no business logic (CLAUDE.md)."""

from functools import lru_cache

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)

from api.deps import CurrentUserId
from configs.settings import get_settings
from generation.provider import get_provider
from ingestion.url_extractor import UrlExtractionError
from retrieval.dense import DenseSearcher
from retrieval.hybrid import HybridRetriever
from retrieval.sparse import SparseSearcher
from services.adzuna_client import DEFAULT_WHAT, AdzunaClient, AdzunaError
from services.jobs_schemas import (
    Job,
    JobCreate,
    JobSearchResponse,
    JobUpdate,
)
from services.jobs_service import JobNotFoundError, JobsService
from services.matching_schemas import MatchAnalysis
from services.matching_service import (
    MatchAnalysisError,
    MatchingService,
    NoProfileError,
)
from storage.repositories import ChunkRepository, JobRepository
from storage.supabase_client import get_supabase

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@lru_cache
def get_adzuna_client() -> AdzunaClient:
    """Process-wide client so the 10-minute search cache is shared."""
    return AdzunaClient(get_settings())


def get_jobs_service() -> JobsService:
    return JobsService(JobRepository(get_supabase()))


def get_matching_service() -> MatchingService:
    client = get_supabase()
    provider = get_provider()
    chunk_repo = ChunkRepository(client)
    return MatchingService(
        provider=provider,
        retriever=HybridRetriever(
            provider=provider,
            dense=DenseSearcher(chunk_repo),
            sparse=SparseSearcher(chunk_repo),
        ),
        chunk_repo=chunk_repo,
        job_repo=JobRepository(client),
    )


ServiceDep = Depends(get_jobs_service)
AdzunaDep = Depends(get_adzuna_client)
MatchingDep = Depends(get_matching_service)


@router.get("/search", response_model=JobSearchResponse)
async def search_jobs(
    user_id: CurrentUserId,  # auth required; value unused
    what: str = Query(default=DEFAULT_WHAT, min_length=2),
    where: str = Query(default=""),
    page: int = Query(default=1, ge=1, le=20),
    adzuna: AdzunaClient = AdzunaDep,
) -> JobSearchResponse:
    try:
        results, count = await adzuna.search(what=what, where=where, page=page)
    except AdzunaError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return JobSearchResponse(results=results, count=count, page=page)


@router.post("", response_model=Job, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    user_id: CurrentUserId,
    background_tasks: BackgroundTasks,
    service: JobsService = ServiceDep,
    matching: MatchingService = MatchingDep,
) -> Job:
    try:
        if body.source == "adzuna":
            job = await service.save_adzuna_job(user_id, body)
        else:
            job = await service.save_manual_job(user_id, body)
    except UrlExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    # Prompt 5: analysis is triggered on save — best-effort, in the background.
    background_tasks.add_task(matching.analyze_quietly, user_id, job.id)
    return job


@router.post("/{job_id}/analyze", response_model=MatchAnalysis)
async def analyze_job(
    job_id: str,
    user_id: CurrentUserId,
    matching: MatchingService = MatchingDep,
) -> MatchAnalysis:
    try:
        return await matching.analyze(user_id, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from exc
    except NoProfileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except MatchAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get("", response_model=list[Job])
async def list_jobs(
    user_id: CurrentUserId,
    job_status: str | None = Query(default=None, alias="status"),
    service: JobsService = ServiceDep,
) -> list[Job]:
    return service.list_jobs(user_id, job_status)


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    user_id: CurrentUserId,
    service: JobsService = ServiceDep,
) -> Job:
    try:
        return service.get_job(user_id, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from exc


@router.patch("/{job_id}", response_model=Job)
async def update_job(
    job_id: str,
    body: JobUpdate,
    user_id: CurrentUserId,
    service: JobsService = ServiceDep,
) -> Job:
    try:
        return service.update_status(user_id, job_id, body.status)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from exc


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    user_id: CurrentUserId,
    service: JobsService = ServiceDep,
) -> None:
    try:
        service.delete_job(user_id, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from exc
