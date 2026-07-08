"""Prompt 5 tests: score-combination math, malformed-LLM-JSON retry then
502-style error, and skill_gaps persistence — all with fakes, no network."""

import json
import time
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from api.jobs import get_jobs_service, get_matching_service
from configs.settings import get_settings
from main import create_app
from retrieval.schemas import RetrievedChunk
from services.jobs_service import JobsService
from services.matching_service import (
    MatchAnalysisError,
    MatchingService,
    NoProfileError,
    combine_scores,
    cosine_similarity,
    mean_vector,
)
from tests.fakes import FakeJobRepo, FakeProvider

USER_ID = "11111111-2222-3333-4444-555555555555"


def auth_header() -> dict[str, str]:
    token = jwt.encode(
        {"sub": USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        get_settings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


VALID_RUBRIC = json.dumps(
    {
        "rubric_score": 80,
        "breakdown": {
            "technical_skills": 85,
            "experience_relevance": 75,
            "education_fit": 90,
            "nice_to_haves": 60,
        },
        "matched_skills": ["Python", "PyTorch"],
        "missing_skills": [
            {
                "name": "Kubernetes",
                "importance": "preferred",
                "evidence": "experience with Kubernetes is a bonus",
            }
        ],
        "one_line_verdict": "Strong technical fit; ops experience is thin.",
    }
)


class EmbeddingProvider(FakeProvider):
    """FakeProvider whose embed() returns a fixed vector (cosine = 1.0)."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeRetriever:
    async def search(
        self, query: str, user_id: str, k: int = 8
    ) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                id="c1",
                section="projects",
                content="Built an LLM eval harness in Python/PyTorch.",
                score=1.0,
            )
        ]


class FakeChunkEmbeddings:
    def __init__(self, embeddings: list[list[float]] | None = None) -> None:
        self.embeddings = (
            embeddings if embeddings is not None else [[1.0, 0.0, 0.0]]
        )

    def list_embeddings(self, user_id: str) -> list[list[float]]:
        return self.embeddings


def make_service(
    responses: list[str],
    job_repo: FakeJobRepo,
    embeddings: list[list[float]] | None = None,
) -> tuple[MatchingService, EmbeddingProvider]:
    provider = EmbeddingProvider(responses)
    service = MatchingService(
        provider=provider,
        retriever=FakeRetriever(),  # type: ignore[arg-type]
        chunk_repo=FakeChunkEmbeddings(embeddings),
        job_repo=job_repo,
    )
    return service, provider


def seed_job(repo: FakeJobRepo, description: str = "x" * 500) -> str:
    row: dict[str, Any] = {
        "source": "manual",
        "title": "ML Intern",
        "description": description,
        "status": "saved",
    }
    return repo.insert(USER_ID, row)["id"]


# ------------------------------------------------------------- score math
def test_combine_scores_weights() -> None:
    assert combine_scores(0.5, 80) == pytest.approx(0.3 * 50 + 0.7 * 80)
    assert combine_scores(0.0, 0) == 0.0
    assert combine_scores(1.0, 100) == 100.0


def test_cosine_similarity_and_mean_vector() -> None:
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([0, 0], [1, 0]) == 0.0  # zero-vector guard
    assert mean_vector([[1, 0], [3, 2]]) == [2.0, 1.0]


# ------------------------------------------------- analysis + persistence
@pytest.mark.asyncio
async def test_analyze_persists_match_score_and_skill_gaps() -> None:
    repo = FakeJobRepo()
    job_id = seed_job(repo)
    service, _ = make_service([VALID_RUBRIC], repo)

    analysis = await service.analyze(USER_ID, job_id)

    # cosine([1,0,0], mean([[1,0,0]])) == 1.0 -> 0.3*100 + 0.7*80 = 86.0
    assert analysis.match_score == pytest.approx(86.0)
    assert analysis.semantic_score == pytest.approx(1.0)
    assert analysis.short_description is False

    stored = repo.rows[job_id]
    assert stored["match_score"] == pytest.approx(86.0)
    gaps = stored["skill_gaps"]
    assert gaps["missing_skills"][0]["name"] == "Kubernetes"
    assert gaps["missing_skills"][0]["importance"] == "preferred"
    assert gaps["missing_skills"][0]["evidence"].startswith("experience with")
    assert gaps["matched_skills"] == ["Python", "PyTorch"]


@pytest.mark.asyncio
async def test_short_description_is_flagged() -> None:
    repo = FakeJobRepo()
    job_id = seed_job(repo, description="Short snippet from Adzuna.")
    service, _ = make_service([VALID_RUBRIC], repo)

    analysis = await service.analyze(USER_ID, job_id)
    assert analysis.short_description is True


@pytest.mark.asyncio
async def test_malformed_json_retries_once_then_succeeds() -> None:
    repo = FakeJobRepo()
    job_id = seed_job(repo)
    service, provider = make_service(["{not json", VALID_RUBRIC], repo)

    analysis = await service.analyze(USER_ID, job_id)
    assert analysis.rubric_score == 80
    assert len(provider.calls) == 2  # first attempt + exactly one retry
    assert "previous output was invalid" in provider.calls[1]["user"]


@pytest.mark.asyncio
async def test_malformed_json_twice_raises_clean_error() -> None:
    repo = FakeJobRepo()
    job_id = seed_job(repo)
    service, provider = make_service(["{not json", "also bad"], repo)

    with pytest.raises(MatchAnalysisError):
        await service.analyze(USER_ID, job_id)
    assert len(provider.calls) == 2
    assert repo.rows[job_id].get("match_score") is None  # nothing persisted


@pytest.mark.asyncio
async def test_no_profile_raises() -> None:
    repo = FakeJobRepo()
    job_id = seed_job(repo)
    service, _ = make_service([VALID_RUBRIC], repo, embeddings=[])

    with pytest.raises(NoProfileError):
        await service.analyze(USER_ID, job_id)


# ------------------------------------------------------------ API surface
@pytest.fixture()
def api() -> tuple[TestClient, FakeJobRepo, list[str]]:
    repo = FakeJobRepo()
    responses: list[str] = []
    app = create_app()
    app.dependency_overrides[get_jobs_service] = lambda: JobsService(repo)
    app.dependency_overrides[get_matching_service] = lambda: make_service(
        responses, repo
    )[0]
    return TestClient(app), repo, responses


def test_analyze_endpoint_returns_analysis(
    api: tuple[TestClient, FakeJobRepo, list[str]],
) -> None:
    client, repo, responses = api
    responses.append(VALID_RUBRIC)
    job_id = seed_job(repo)

    res = client.post(f"/api/jobs/{job_id}/analyze", headers=auth_header())
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["match_score"] == pytest.approx(86.0)
    assert body["one_line_verdict"]


def test_analyze_endpoint_502_on_persistent_bad_llm_json(
    api: tuple[TestClient, FakeJobRepo, list[str]],
) -> None:
    client, repo, responses = api
    responses.extend(["bad", "still bad"])
    job_id = seed_job(repo)

    res = client.post(f"/api/jobs/{job_id}/analyze", headers=auth_header())
    assert res.status_code == 502
    assert "retry" in res.json()["detail"].lower()


def test_analyze_endpoint_404_for_unknown_job(
    api: tuple[TestClient, FakeJobRepo, list[str]],
) -> None:
    client, _, _ = api
    res = client.post("/api/jobs/nope/analyze", headers=auth_header())
    assert res.status_code == 404
