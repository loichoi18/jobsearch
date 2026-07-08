"""Prompt 4 tests: Adzuna mapping, manual intake validation, blocked-fetch
guidance, and job CRUD through the API with a fake repository."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.jobs import get_jobs_service, get_matching_service
from configs.settings import get_settings
from ingestion.url_extractor import (
    UrlExtractionError,
    extract_jd_from_url,
    is_blocked_domain,
)
from main import create_app
from services.adzuna_client import map_result
from services.jobs_schemas import ManualJobCreate
from services.jobs_service import JobsService
from tests.fakes import FakeJobRepo, FakeMatchingService

FIXTURES = Path(__file__).parent / "fixtures"
ADZUNA_FIXTURE = json.loads(
    (FIXTURES / "adzuna_search.json").read_text(encoding="utf-8")
)
USER_ID = "11111111-2222-3333-4444-555555555555"


def auth_header() -> dict[str, str]:
    token = jwt.encode(
        {"sub": USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        get_settings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def repo() -> FakeJobRepo:
    return FakeJobRepo()


@pytest.fixture()
def client(repo: FakeJobRepo) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_jobs_service] = lambda: JobsService(repo)
    app.dependency_overrides[get_matching_service] = FakeMatchingService
    return TestClient(app)


# ---------------------------------------------------------------- mapping
def test_adzuna_mapping_from_fixture() -> None:
    first = map_result(ADZUNA_FIXTURE["results"][0])
    assert first.adzuna_id == "5001234567"
    assert first.title == "Machine Learning Internship"
    assert first.company == "Atlassian"
    assert first.location == "Sydney, New South Wales"
    assert first.salary_min == 60000
    assert first.redirect_url.endswith("/5001234567")

    second = map_result(ADZUNA_FIXTURE["results"][1])
    assert second.salary_min is None and second.salary_max is None


# ------------------------------------------------------ manual validation
def test_manual_intake_requires_description_or_url() -> None:
    with pytest.raises(ValidationError):
        ManualJobCreate(source="manual", title="ML Intern")


def test_manual_intake_accepts_description_only() -> None:
    body = ManualJobCreate(
        source="manual", title="ML Intern", description="Build eval tooling."
    )
    assert body.url is None


# ------------------------------------------------------- blocked fetches
def test_seek_and_linkedin_domains_are_blocked() -> None:
    assert is_blocked_domain("https://www.seek.com.au/job/123")
    assert is_blocked_domain("https://au.linkedin.com/jobs/view/456")
    assert not is_blocked_domain("https://careers.atlassian.com/job/789")


@pytest.mark.asyncio
async def test_blocked_domain_raises_paste_guidance_without_fetching() -> None:
    with patch("ingestion.url_extractor.httpx.AsyncClient") as mock_client:
        with pytest.raises(UrlExtractionError, match="paste"):
            await extract_jd_from_url("https://www.seek.com.au/job/123")
        mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_failed_fetch_raises_paste_guidance() -> None:
    mock_get = AsyncMock(side_effect=httpx.ConnectError("blocked"))
    with patch("ingestion.url_extractor.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = mock_get
        with pytest.raises(UrlExtractionError, match="paste"):
            await extract_jd_from_url("https://example.com/job/1")


def test_api_returns_422_with_guidance_for_blocked_url(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/jobs",
        json={
            "source": "manual",
            "title": "Data Intern",
            "url": "https://www.seek.com.au/job/123",
        },
        headers=auth_header(),
    )
    assert response.status_code == 422
    assert "paste" in response.json()["detail"].lower()


# ------------------------------------------------------------- CRUD flow
def test_save_adzuna_then_manual_then_list(client: TestClient) -> None:
    saved = client.post(
        "/api/jobs",
        json={
            "source": "adzuna",
            "payload": {
                "adzuna_id": "5001234567",
                "title": "Machine Learning Internship",
                "company": "Atlassian",
                "location": "Sydney",
                "snippet": "ML platform team...",
                "redirect_url": "https://www.adzuna.com.au/details/5001234567",
            },
        },
        headers=auth_header(),
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["source"] == "adzuna"
    assert saved.json()["status"] == "saved"

    manual = client.post(
        "/api/jobs",
        json={
            "source": "manual",
            "title": "Graduate AI Engineer",
            "company": "Canva",
            "description": "Pasted Seek JD text about RAG systems...",
        },
        headers=auth_header(),
    )
    assert manual.status_code == 201, manual.text

    listing = client.get("/api/jobs", headers=auth_header())
    assert listing.status_code == 200
    assert len(listing.json()) == 2


def test_status_patch_and_invalid_status_rejected(client: TestClient) -> None:
    job_id = client.post(
        "/api/jobs",
        json={"source": "manual", "title": "X", "description": "A JD."},
        headers=auth_header(),
    ).json()["id"]

    ok = client.patch(
        f"/api/jobs/{job_id}", json={"status": "applied"}, headers=auth_header()
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "applied"

    bad = client.patch(
        f"/api/jobs/{job_id}",
        json={"status": "daydreaming"},
        headers=auth_header(),
    )
    assert bad.status_code == 422


def test_delete_and_404s(client: TestClient) -> None:
    job_id = client.post(
        "/api/jobs",
        json={"source": "manual", "title": "X", "description": "A JD."},
        headers=auth_header(),
    ).json()["id"]

    assert (
        client.delete(f"/api/jobs/{job_id}", headers=auth_header()).status_code
        == 204
    )
    assert (
        client.get(f"/api/jobs/{job_id}", headers=auth_header()).status_code
        == 404
    )
    assert (
        client.delete(f"/api/jobs/{job_id}", headers=auth_header()).status_code
        == 404
    )


# ------------------------------------------------- applied_at (Prompt 8)
def test_moving_to_applied_sets_applied_at_once(client: TestClient) -> None:
    job_id = client.post(
        "/api/jobs",
        json={"source": "manual", "title": "X", "description": "A JD."},
        headers=auth_header(),
    ).json()["id"]

    first = client.patch(
        f"/api/jobs/{job_id}", json={"status": "applied"}, headers=auth_header()
    ).json()
    assert first["applied_at"] is not None

    # Move away and back — applied_at must not change
    client.patch(
        f"/api/jobs/{job_id}",
        json={"status": "interview"},
        headers=auth_header(),
    )
    second = client.patch(
        f"/api/jobs/{job_id}", json={"status": "applied"}, headers=auth_header()
    ).json()
    assert second["applied_at"] == first["applied_at"]


def test_non_applied_transitions_do_not_set_applied_at(
    client: TestClient,
) -> None:
    job_id = client.post(
        "/api/jobs",
        json={"source": "manual", "title": "X", "description": "A JD."},
        headers=auth_header(),
    ).json()["id"]
    moved = client.patch(
        f"/api/jobs/{job_id}",
        json={"status": "interview"},
        headers=auth_header(),
    ).json()
    assert moved.get("applied_at") is None
