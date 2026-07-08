"""Extractor: happy path, retry-on-invalid, and hard failure."""

import json
from pathlib import Path

import pytest

from ingestion.profile_extractor import ProfileExtractionError, extract_profile
from tests.fakes import FakeProvider

FIXTURE = Path(__file__).parent / "fixtures" / "profile_extraction.json"
VALID_JSON = FIXTURE.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_extracts_valid_profile() -> None:
    provider = FakeProvider([VALID_JSON])
    profile = await extract_profile("raw cv text", provider)

    assert profile.education[0].institution == "UTS"
    assert profile.projects[0].name == "Model Regression Detection"
    assert "Python" in profile.skills.technical
    assert profile.visa_status == "Australian citizen"
    assert len(provider.calls) == 1
    assert provider.calls[0]["schema"] is not None


@pytest.mark.asyncio
async def test_retries_once_on_invalid_json() -> None:
    provider = FakeProvider(["not valid json {", VALID_JSON])
    profile = await extract_profile("raw cv text", provider)

    assert profile.education[0].institution == "UTS"
    assert len(provider.calls) == 2
    # Retry prompt must feed the validation error back to the model
    assert "invalid" in provider.calls[1]["user"].lower()


@pytest.mark.asyncio
async def test_fails_after_two_invalid_responses() -> None:
    bad = json.dumps({"education": "this-should-be-a-list"})
    provider = FakeProvider(["nope", bad])

    with pytest.raises(ProfileExtractionError):
        await extract_profile("raw cv text", provider)
    assert len(provider.calls) == 2
