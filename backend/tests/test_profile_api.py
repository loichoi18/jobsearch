"""Integration tests for the profile endpoints: real FastAPI app, real JWT
verification, fixture PDF — fake repo and fake LLM provider."""

import time
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from api.profile import get_profile_service
from configs.settings import get_settings
from main import create_app
from services.profile_service import ProfileService
from tests.fakes import FakeProfileRepo, FakeProvider

FIXTURES = Path(__file__).parent / "fixtures"
VALID_JSON = (FIXTURES / "profile_extraction.json").read_text(encoding="utf-8")

USER_ID = "11111111-2222-3333-4444-555555555555"


def mint_token(user_id: str = USER_ID) -> str:
    return jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600},
        get_settings().supabase_jwt_secret,
        algorithm="HS256",
    )


def auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_token()}"}


@pytest.fixture()
def repo() -> FakeProfileRepo:
    return FakeProfileRepo()


@pytest.fixture()
def client(repo: FakeProfileRepo) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_profile_service] = lambda: ProfileService(
        repo=repo, provider=FakeProvider([VALID_JSON])
    )
    return TestClient(app)


def test_upload_pdf_extracts_and_persists(
    client: TestClient, repo: FakeProfileRepo
) -> None:
    pdf_bytes = (FIXTURES / "sample_cv.pdf").read_bytes()
    response = client.post(
        "/api/profile/upload",
        files={"file": ("cv.pdf", pdf_bytes, "application/pdf")},
        headers=auth_header(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["structured"]["education"][0]["institution"] == "UTS"
    # Persisted with raw text, keyed by the JWT-derived user id
    stored = repo.rows[USER_ID]
    assert "Model Regression Detection" in stored["raw_text"]


def test_upload_rejects_non_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/profile/upload",
        files={"file": ("cv.txt", b"plain text", "text/plain")},
        headers=auth_header(),
    )
    assert response.status_code == 415


def test_requests_without_token_are_401(client: TestClient) -> None:
    assert client.get("/api/profile").status_code == 401


def test_requests_with_bad_token_are_401(client: TestClient) -> None:
    response = client.get(
        "/api/profile", headers={"Authorization": "Bearer garbage"}
    )
    assert response.status_code == 401


def test_get_returns_404_before_any_upload(client: TestClient) -> None:
    response = client.get("/api/profile", headers=auth_header())
    assert response.status_code == 404


def test_put_updates_and_get_roundtrips(
    client: TestClient, repo: FakeProfileRepo
) -> None:
    import json

    structured = json.loads(VALID_JSON)
    structured["visa_status"] = "Student visa (subclass 500)"

    put = client.put("/api/profile", json=structured, headers=auth_header())
    assert put.status_code == 200

    got = client.get("/api/profile", headers=auth_header())
    assert got.status_code == 200
    assert got.json()["structured"]["visa_status"] == "Student visa (subclass 500)"
