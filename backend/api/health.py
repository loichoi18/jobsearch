"""Health check router. Routers contain no business logic (CLAUDE.md)."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe used by Render health checks and the frontend."""
    return HealthResponse(status="ok", service="jobpilot-au-api")
