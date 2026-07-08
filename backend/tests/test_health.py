"""The health endpoint must return 200 with the expected payload."""

from fastapi.testclient import TestClient

from main import create_app


def test_health_returns_200() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "jobpilot-au-api"
