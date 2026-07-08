"""Evaluation-run endpoints (Prompt 11). Read-only view of the harness's runs
for the /evals page. Routers hold no business logic (CLAUDE.md).

eval_runs is a global demo table (no user_id), but the endpoints still require
a valid session so the page isn't fully public.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import CurrentUserId
from storage.repositories import EvalRunRepository
from storage.supabase_client import get_supabase

router = APIRouter(prefix="/api/evals", tags=["evals"])


def get_eval_repo() -> EvalRunRepository:
    return EvalRunRepository(get_supabase())


RepoDep = Depends(get_eval_repo)


@router.get("/runs")
async def list_runs(
    user_id: CurrentUserId,
    repo: EvalRunRepository = RepoDep,
) -> list[dict[str, Any]]:
    return repo.list_recent()


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    user_id: CurrentUserId,
    repo: EvalRunRepository = RepoDep,
) -> dict[str, Any]:
    row = repo.get(run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found"
        )
    return row
