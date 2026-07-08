"""Shared test fixtures. Injects dummy env vars BEFORE any app import so
settings never depend on a developer's real .env during unit tests.
"""

import os

import pytest

_TEST_ENV = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret-not-for-production-use",
    "GEMINI_API_KEY": "test-gemini-key",
    "ADZUNA_APP_ID": "test-adzuna-id",
    "ADZUNA_APP_KEY": "test-adzuna-key",
    "FRONTEND_URL": "http://localhost:3000",
}

for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)


@pytest.fixture()
def test_env() -> dict[str, str]:
    """The env values active during tests, for assertions."""
    return dict(_TEST_ENV)
