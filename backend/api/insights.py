"""Skill-gap insight endpoints. Routers hold no business logic (CLAUDE.md)."""

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import CurrentUserId
from generation.provider import get_provider
from services.insights_schemas import SkillGapsResponse, UpskillPlan
from services.insights_service import (
    InsightsService,
    UpskillPlanError,
    get_shared_plan_cache,
)
from storage.repositories import JobRepository, ProfileRepository
from storage.supabase_client import get_supabase

router = APIRouter(prefix="/api/insights", tags=["insights"])


def get_insights_service() -> InsightsService:
    client = get_supabase()
    return InsightsService(
        job_repo=JobRepository(client),
        profile_repo=ProfileRepository(client),
        provider=get_provider(),
        plan_cache=get_shared_plan_cache(),
    )


ServiceDep = Depends(get_insights_service)


@router.get("/skill-gaps", response_model=SkillGapsResponse)
async def skill_gaps(
    user_id: CurrentUserId,
    service: InsightsService = ServiceDep,
) -> SkillGapsResponse:
    return service.skill_gaps(user_id)


@router.post("/upskill-plan", response_model=UpskillPlan)
async def upskill_plan(
    user_id: CurrentUserId,
    service: InsightsService = ServiceDep,
) -> UpskillPlan:
    try:
        return await service.upskill_plan(user_id)
    except UpskillPlanError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
