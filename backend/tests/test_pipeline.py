"""Prompt 6 tests: full pipeline with a mocked provider, unsupported-claim
removal, grounding math, the one-revision-cycle limit, version auto-increment,
and the background-generation API flow."""

import json
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from api.documents import get_generation_service
from configs.settings import get_settings
from generation.doc_schemas import (
    DraftDocument,
    DraftSection,
    DraftUnit,
    VerifierResult,
)
from generation.pipeline import (
    GenerationPipeline,
    PipelineError,
    compute_grounding,
)
from main import create_app
from retrieval.schemas import RetrievedChunk
from services.generation_service import GenerationService
from tests.fakes import (
    FakeDocumentRepo,
    FakeJobRepo,
    FakeProfileRepo,
    FakeProvider,
)

USER_ID = "11111111-2222-3333-4444-555555555555"
PROFILE = {"skills": {"technical": ["Python", "PyTorch"]}}


def auth_header() -> dict[str, str]:
    token = jwt.encode(
        {"sub": USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        get_settings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class FakeRetriever:
    async def search(
        self, query: str, user_id: str, k: int = 12
    ) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                id="c1",
                section="projects",
                content="Built an LLM eval harness in Python and PyTorch.",
                score=1.0,
            ),
            RetrievedChunk(
                id="c2",
                section="education",
                content="BSc Computer Science, UTS, 2025.",
                score=0.8,
            ),
        ]


# ------------------------------------------------------------ fixtures
DRAFT = json.dumps(
    {
        "doc_type": "cover_letter",
        "sections": [
            {
                "title": "letter",
                "units": [
                    {"text": "Your ML platform role fits my focus.", "chunk_ids": []},
                    {"text": "I built an LLM eval harness in Python.", "chunk_ids": ["c1"]},
                    {"text": "I led a team of 12 engineers at Google.", "chunk_ids": ["c1"]},
                    {"text": "I would welcome a conversation.", "chunk_ids": []},
                ],
            }
        ],
    }
)

REVIEW_WITH_FIXES = json.dumps(
    {
        "scores": {
            "keyword_coverage": 70,
            "specificity": 60,
            "structure": 80,
            "tone": 75,
            "red_flags": 50,
        },
        "mandatory_fixes": ["Paragraph 3 is suspicious — verify or cut."],
        "suggestions": ["Mention the company name in the close."],
    }
)

REVIEW_CLEAN = json.dumps(
    {
        "scores": {
            "keyword_coverage": 85,
            "specificity": 80,
            "structure": 85,
            "tone": 85,
            "red_flags": 95,
        },
        "mandatory_fixes": [],
        "suggestions": [],
    }
)

REVISED_DRAFT = DRAFT  # same shape; revision content identical is fine for tests

VERIFIER = json.dumps(
    {
        "checks": [
            {"index": 0, "verdict": "grounded", "note": None},
            {"index": 1, "verdict": "grounded", "note": None},
            {
                "index": 2,
                "verdict": "unsupported",
                "note": "Cited chunk says nothing about Google or leading 12.",
            },
            {"index": 3, "verdict": "grounded", "note": None},
        ]
    }
)


def make_pipeline(responses: list[str]) -> tuple[GenerationPipeline, FakeProvider]:
    provider = FakeProvider(responses)
    pipeline = GenerationPipeline(
        provider=provider, retriever=FakeRetriever()  # type: ignore[arg-type]
    )
    return pipeline, provider


# ------------------------------------------------------- grounding math
def test_compute_grounding_removes_unsupported_and_computes_rate() -> None:
    document = DraftDocument.model_validate(json.loads(DRAFT))
    verifier = VerifierResult.model_validate(json.loads(VERIFIER))

    cleaned, report = compute_grounding(document, verifier)

    assert report.grounding_rate == pytest.approx(3 / 4)
    assert report.removed_claims == ["I led a team of 12 engineers at Google."]
    texts = [u.text for u in cleaned.all_units()]
    assert "I led a team of 12 engineers at Google." not in texts
    assert len(texts) == 3
    # The report still lists ALL claims, including the removed one
    assert len(report.claims) == 4


def test_compute_grounding_treats_unaudited_claims_as_unsupported() -> None:
    document = DraftDocument(
        doc_type="cv",
        sections=[
            DraftSection(
                title="Projects",
                units=[
                    DraftUnit(text="A", chunk_ids=["c1"]),
                    DraftUnit(text="B", chunk_ids=["c1"]),
                ],
            )
        ],
    )
    verifier = VerifierResult.model_validate(
        {"checks": [{"index": 0, "verdict": "grounded"}]}
    )
    cleaned, report = compute_grounding(document, verifier)
    assert report.grounding_rate == pytest.approx(0.5)
    assert [u.text for u in cleaned.all_units()] == ["A"]


def test_compute_grounding_drops_emptied_sections() -> None:
    document = DraftDocument(
        doc_type="cv",
        sections=[
            DraftSection(title="Fluff", units=[DraftUnit(text="X")]),
            DraftSection(title="Real", units=[DraftUnit(text="Y", chunk_ids=["c1"])]),
        ],
    )
    verifier = VerifierResult.model_validate(
        {
            "checks": [
                {"index": 0, "verdict": "unsupported"},
                {"index": 1, "verdict": "grounded"},
            ]
        }
    )
    cleaned, _ = compute_grounding(document, verifier)
    assert [s.title for s in cleaned.sections] == ["Real"]


# ------------------------------------------------------------- pipeline
@pytest.mark.asyncio
async def test_full_pipeline_with_revision_cycle() -> None:
    pipeline, provider = make_pipeline(
        [DRAFT, REVIEW_WITH_FIXES, REVISED_DRAFT, VERIFIER]
    )
    result = await pipeline.generate(
        USER_ID, "cover_letter", "We need Python for our ML platform.", PROFILE
    )

    # Exactly 4 LLM calls: draft, review, ONE revision, verify
    assert len(provider.calls) == 4
    assert result.grounding.grounding_rate == pytest.approx(0.75)
    assert result.grounding.removed_claims == [
        "I led a team of 12 engineers at Google."
    ]
    # Fabricated claim never survives to the final document
    final_texts = [u.text for u in result.document.all_units()]
    assert "I led a team of 12 engineers at Google." not in final_texts


@pytest.mark.asyncio
async def test_no_revision_when_reviewer_has_no_mandatory_fixes() -> None:
    pipeline, provider = make_pipeline([DRAFT, REVIEW_CLEAN, VERIFIER])
    await pipeline.generate(USER_ID, "cover_letter", "JD text here.", PROFILE)
    assert len(provider.calls) == 3  # draft, review, verify — no revision


@pytest.mark.asyncio
async def test_reviewer_gets_fresh_context() -> None:
    pipeline, provider = make_pipeline([DRAFT, REVIEW_CLEAN, VERIFIER])
    await pipeline.generate(USER_ID, "cover_letter", "JD text here.", PROFILE)

    reviewer_call = provider.calls[1]
    # Reviewer sees JD + draft only: no profile JSON, no retrieved chunks
    assert "PyTorch" not in reviewer_call["user"]  # profile content
    assert "eval harness in Python and PyTorch" not in reviewer_call["user"]
    assert "JD text here." in reviewer_call["user"]
    assert "sceptical senior recruiter" in reviewer_call["system"]


@pytest.mark.asyncio
async def test_stage_failure_after_retry_raises_pipeline_error() -> None:
    pipeline, provider = make_pipeline(["not json", "still not json"])
    with pytest.raises(PipelineError):
        await pipeline.generate(USER_ID, "cv", "JD.", PROFILE)
    assert len(provider.calls) == 2  # one attempt + one retry, then stop


# -------------------------------------------------------- service + API
def make_service(
    responses: list[str],
) -> tuple[GenerationService, FakeDocumentRepo, FakeJobRepo]:
    pipeline, _ = make_pipeline(responses)
    doc_repo = FakeDocumentRepo()
    job_repo = FakeJobRepo()
    profile_repo = FakeProfileRepo()
    profile_repo.upsert(USER_ID, PROFILE, "raw")
    service = GenerationService(
        pipeline=pipeline,
        doc_repo=doc_repo,
        job_repo=job_repo,
        profile_repo=profile_repo,
    )
    return service, doc_repo, job_repo


def seed_job(job_repo: FakeJobRepo) -> str:
    return job_repo.insert(
        USER_ID,
        {
            "source": "manual",
            "title": "ML Intern",
            "description": "Python ML platform role." * 30,
            "status": "saved",
        },
    )["id"]


@pytest.mark.asyncio
async def test_versions_auto_increment_per_job_and_doc_type() -> None:
    service, doc_repo, job_repo = make_service(
        [DRAFT, REVIEW_CLEAN, VERIFIER, DRAFT, REVIEW_CLEAN, VERIFIER]
    )
    job_id = seed_job(job_repo)

    first = service.start_generation(USER_ID, job_id, "cover_letter")
    await service.run_generation(USER_ID, job_id, first["id"], "cover_letter")
    second = service.start_generation(USER_ID, job_id, "cover_letter")

    assert first["version"] == 1
    assert second["version"] == 2
    assert doc_repo.rows[first["id"]]["status"] == "complete"
    report = doc_repo.rows[first["id"]]["grounding_report"]
    assert report["grounding_rate"] == pytest.approx(0.75)


@pytest.mark.asyncio
async def test_failed_run_marks_document_failed() -> None:
    service, doc_repo, job_repo = make_service(["bad", "bad"])
    job_id = seed_job(job_repo)
    row = service.start_generation(USER_ID, job_id, "cv")

    await service.run_generation(USER_ID, job_id, row["id"], "cv")

    stored = doc_repo.rows[row["id"]]
    assert stored["status"] == "failed"
    assert "failed after retry" in stored["error"]


def test_generate_endpoint_background_flow() -> None:
    service, doc_repo, job_repo = make_service([DRAFT, REVIEW_CLEAN, VERIFIER])
    job_id = seed_job(job_repo)

    app = create_app()
    app.dependency_overrides[get_generation_service] = lambda: service
    client = TestClient(app)

    res = client.post(
        f"/api/jobs/{job_id}/generate",
        json={"doc_type": "cover_letter"},
        headers=auth_header(),
    )
    assert res.status_code == 202, res.text
    doc_id = res.json()["document_id"]
    assert res.json()["status"] == "pending"

    # TestClient runs background tasks before returning — poll shows complete
    poll = client.get(f"/api/documents/{doc_id}", headers=auth_header())
    assert poll.status_code == 200
    body = poll.json()
    assert body["status"] == "complete"
    assert body["grounding_report"]["grounding_rate"] == pytest.approx(0.75)

    listing = client.get(
        f"/api/jobs/{job_id}/documents", headers=auth_header()
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_generate_endpoint_404_and_409() -> None:
    service, _, job_repo = make_service([])
    app = create_app()
    app.dependency_overrides[get_generation_service] = lambda: service
    client = TestClient(app)

    missing = client.post(
        "/api/jobs/nope/generate",
        json={"doc_type": "cv"},
        headers=auth_header(),
    )
    assert missing.status_code == 404

    # No profile: fresh service whose profile repo is empty
    pipeline, _ = make_pipeline([])
    bare = GenerationService(
        pipeline=pipeline,
        doc_repo=FakeDocumentRepo(),
        job_repo=job_repo,
        profile_repo=FakeProfileRepo(),
    )
    app.dependency_overrides[get_generation_service] = lambda: bare
    job_id = seed_job(job_repo)
    res = client.post(
        f"/api/jobs/{job_id}/generate",
        json={"doc_type": "cv"},
        headers=auth_header(),
    )
    assert res.status_code == 409
