"""JobPilot AU backend — FastAPI application entrypoint.

Run locally:  uvicorn main:app --reload --port 8000  (from backend/)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from api.documents import router as documents_router
from api.enhance import router as enhance_router
from api.evals import router as evals_router
from api.health import router as health_router
from api.insights import router as insights_router
from api.jobs import router as jobs_router
from api.profile import router as profile_router
from api.retrieval import router as retrieval_router
from api.rate_limit import limiter, rate_limit_handler
from configs.settings import get_settings


def create_app() -> FastAPI:
    """Application factory: builds the FastAPI app with CORS and routers."""
    settings = get_settings()

    app = FastAPI(
        title="JobPilot AU API",
        version="1.0.0",
        description="AI job-application copilot for the Australian graduate market.",
    )

    # Per-user rate limiting (Prompt 12): the generation endpoints hit a free
    # LLM tier, so a public demo needs a ceiling. See api/rate_limit.py.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    allowed_origins = {"http://localhost:3000", settings.frontend_url}
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(profile_router)
    app.include_router(retrieval_router)
    app.include_router(jobs_router)
    app.include_router(documents_router)
    app.include_router(enhance_router)
    app.include_router(insights_router)
    app.include_router(evals_router)

    return app


app = create_app()
