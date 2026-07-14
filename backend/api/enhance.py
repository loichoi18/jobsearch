"""CV-enhance endpoint. Routers hold no business logic (CLAUDE.md)."""

from fastapi import APIRouter, HTTPException, Request, status

from api.deps import CurrentUserId
from api.rate_limit import GENERATION_RATE_LIMIT, limiter
from generation.provider import get_provider
from services.enhance_schemas import EnhanceCvRequest, EnhanceCvResponse
from services.enhance_service import EnhanceCvError, EnhanceCvService

router = APIRouter(prefix="/api/enhance", tags=["enhance"])


def get_enhance_service() -> EnhanceCvService:
    return EnhanceCvService(provider=get_provider())


@router.post("/cv", response_model=EnhanceCvResponse)
@limiter.limit(GENERATION_RATE_LIMIT)
async def enhance_cv(
    request: Request,
    body: EnhanceCvRequest,
    user_id: CurrentUserId,
) -> EnhanceCvResponse:
    try:
        result = await get_enhance_service().enhance(
            company_name=body.company_name,
            resume=body.resume,
            job_description=body.job_description,
        )
    except EnhanceCvError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return EnhanceCvResponse(result=result)
