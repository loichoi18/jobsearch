"""Chunker: one chunk per semantic unit, correct metadata, no empty chunks."""

import json
from pathlib import Path

from ingestion.chunker import chunk_profile
from ingestion.profile_schema import Profile

FIXTURE = Path(__file__).parent / "fixtures" / "profile_extraction.json"
PROFILE = Profile.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_each_semantic_unit_is_its_own_chunk() -> None:
    chunks = chunk_profile(PROFILE)
    sections = [c.section for c in chunks]

    # Fixture: 1 education, 0 experience, 1 project, technical+tools skills, visa+link
    assert sections.count("education") == 1
    assert sections.count("experience") == 0
    assert sections.count("project") == 1
    assert sections.count("skills") == 2  # technical + tools (soft is empty)
    assert sections.count("basics") == 1


def test_chunk_content_and_metadata() -> None:
    chunks = chunk_profile(PROFILE)
    project = next(c for c in chunks if c.section == "project")

    assert project.title == "Model Regression Detection"
    assert "eval harness" in project.content
    assert "MLflow" in project.content
    assert project.metadata == {
        "section": "project",
        "title": "Model Regression Detection",
    }


def test_no_empty_chunks_and_reasonable_size() -> None:
    chunks = chunk_profile(PROFILE)
    assert chunks, "fixture profile must produce chunks"
    for chunk in chunks:
        assert chunk.content.strip()
        # ~4 chars/token heuristic; semantic units should stay under ~300 tokens
        assert len(chunk.content) < 1200


def test_empty_profile_produces_no_chunks() -> None:
    assert chunk_profile(Profile()) == []
