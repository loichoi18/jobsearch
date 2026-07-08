"""Prompt 7 tests: cutting score function, 2-page loop termination, header
building, and a real Typst compile (skipped when the binary is absent)."""

import shutil

import pytest

from generation.cutting import (
    bullet_score,
    cut_lowest_bullet,
    tokenize,
)
from generation.doc_schemas import DraftDocument, DraftSection, DraftUnit
from generation.renderer import (
    build_header,
    compile_typst,
    enforce_page_limit,
)

JD = "We need Python and PyTorch experience for our ML platform team."


def make_cv(bullets: list[tuple[str, list[str]]]) -> DraftDocument:
    return DraftDocument(
        doc_type="cv",
        sections=[
            DraftSection(
                title="Projects",
                units=[DraftUnit(text=t, chunk_ids=c) for t, c in bullets],
            )
        ],
    )


# ------------------------------------------------------------ score maths
def test_relevant_bullet_outscores_irrelevant() -> None:
    jd_tokens = tokenize(JD)
    relevant = DraftUnit(text="Built PyTorch models in Python for ML.")
    irrelevant = DraftUnit(text="Organised the office social calendar.")
    others: list[DraftUnit] = []
    assert bullet_score(relevant, jd_tokens, others, frozenset()) > bullet_score(
        irrelevant, jd_tokens, others, frozenset()
    )


def test_duplicate_bullets_lose_uniqueness() -> None:
    jd_tokens = tokenize(JD)
    a = DraftUnit(text="Built PyTorch models in Python")
    twin = DraftUnit(text="Built PyTorch models in Python")
    distinct = DraftUnit(text="Deployed the eval harness to production")
    assert bullet_score(a, jd_tokens, [twin], frozenset()) < bullet_score(
        a, jd_tokens, [distinct], frozenset()
    )


def test_cover_letter_dependency_boosts_score() -> None:
    jd_tokens = tokenize(JD)
    unit = DraftUnit(text="Built PyTorch models", chunk_ids=["c1"])
    base = bullet_score(unit, jd_tokens, [], frozenset())
    boosted = bullet_score(unit, jd_tokens, [], frozenset({"c1"}))
    assert boosted == pytest.approx(base * 1.3)


def test_cut_lowest_removes_least_relevant_and_drops_empty_sections() -> None:
    document = DraftDocument(
        doc_type="cv",
        sections=[
            DraftSection(
                title="Fluff",
                units=[DraftUnit(text="Enjoy long walks and hobbies.")],
            ),
            DraftSection(
                title="Projects",
                units=[DraftUnit(text="Built PyTorch ML models in Python.")],
            ),
        ],
    )
    cut_doc, cut_text = cut_lowest_bullet(document, JD)
    assert cut_text == "Enjoy long walks and hobbies."
    assert [s.title for s in cut_doc.sections] == ["Projects"]


def test_cut_refuses_to_empty_the_document() -> None:
    document = make_cv([("Only bullet.", [])])
    same_doc, cut_text = cut_lowest_bullet(document, JD)
    assert cut_text is None
    assert len(same_doc.all_units()) == 1


# ----------------------------------------------------------- page limiting
def test_enforce_page_limit_cuts_until_it_fits() -> None:
    document = make_cv(
        [(f"Bullet number {i} about topic {i}.", []) for i in range(8)]
    )

    def fake_render(doc: DraftDocument) -> tuple[bytes, int]:
        # 2 bullets per page: 8 -> 4 pages; fits at 4 bullets.
        units = len(doc.all_units())
        return b"%PDF-fake", (units + 1) // 2

    outcome = enforce_page_limit(document, fake_render, JD, max_pages=2)
    assert outcome.pages <= 2
    assert len(outcome.document.all_units()) == 4
    assert len(outcome.cut_bullets) == 4


def test_enforce_page_limit_stops_at_max_iterations() -> None:
    document = make_cv([(f"Bullet {i}.", []) for i in range(20)])
    calls = {"n": 0}

    def stubborn_render(doc: DraftDocument) -> tuple[bytes, int]:
        calls["n"] += 1
        return b"%PDF-fake", 99  # never fits

    outcome = enforce_page_limit(
        document, stubborn_render, JD, max_pages=2, max_iterations=10
    )
    assert len(outcome.cut_bullets) == 10  # exactly max_iterations cuts
    assert calls["n"] == 11  # initial render + one per cut
    assert outcome.pages == 99  # accepted, logged, not raised


# ----------------------------------------------------------------- header
def test_build_header_joins_contact_parts() -> None:
    header = build_header(
        {
            "name": "Lucas Luong",
            "email": "lucas@example.com",
            "phone": None,
            "location": "Sydney",
            "links": {"github": "github.com/lucas"},
        }
    )
    assert header["name"] == "Lucas Luong"
    assert header["contact_line"] == "lucas@example.com · Sydney · github.com/lucas"


# ------------------------------------------------------- real typst compile
requires_typst = pytest.mark.skipif(
    shutil.which("typst") is None, reason="typst binary not installed"
)


@requires_typst
def test_real_typst_compile_produces_valid_pdf() -> None:
    document = make_cv(
        [
            ("Built an LLM evaluation harness in Python.", ["c1"]),
            ("Deployed RAG retrieval with pgvector.", ["c2"]),
        ]
    )
    header = {"name": "Test Candidate", "contact_line": "test@example.com"}
    pdf_bytes, pages = compile_typst(document, header, "typst")
    assert pdf_bytes.startswith(b"%PDF")
    assert pages == 1


@requires_typst
def test_real_typst_compile_cover_letter() -> None:
    document = DraftDocument(
        doc_type="cover_letter",
        sections=[
            DraftSection(
                title="letter",
                units=[DraftUnit(text=f"Paragraph {i}.") for i in range(4)],
            )
        ],
    )
    header = {"name": "Test Candidate", "contact_line": ""}
    pdf_bytes, pages = compile_typst(document, header, "typst")
    assert pdf_bytes.startswith(b"%PDF")
    assert pages == 1


# --------------------------------------------- service render integration
import json

from generation.renderer import RenderOutcome
from services.generation_service import GenerationService
from tests.fakes import FakeDocumentRepo, FakeJobRepo, FakeProfileRepo, FakeProvider

USER_ID = "11111111-2222-3333-4444-555555555555"

CV_DRAFT = json.dumps(
    {
        "doc_type": "cv",
        "sections": [
            {
                "title": "Projects",
                "units": [
                    {"text": "Built an eval harness in Python.", "chunk_ids": ["c1"]}
                ],
            }
        ],
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
VERIFIER_OK = json.dumps(
    {"checks": [{"index": 0, "verdict": "grounded", "note": None}]}
)


class FakeRetrieverR:
    async def search(self, query, user_id, k=12):
        from retrieval.schemas import RetrievedChunk

        return [
            RetrievedChunk(
                id="c1", section="projects", content="Eval harness.", score=1.0
            )
        ]


class FakeRenderer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def render(self, document, structured_profile, jd_text="", cover_letter_chunk_ids=frozenset()):
        self.calls.append(
            {"doc_type": document.doc_type, "cl_ids": cover_letter_chunk_ids}
        )
        return RenderOutcome(
            pdf_bytes=b"%PDF-fake", pages=1, document=document, cut_bullets=[]
        )


class FakePdfStorage:
    def __init__(self) -> None:
        self.uploads: dict[str, bytes] = {}

    def upload(self, path: str, pdf_bytes: bytes) -> str:
        self.uploads[path] = pdf_bytes
        return path

    def signed_url(self, path: str, expires_s: int = 300) -> str:
        return f"https://signed.example/{path}?exp={expires_s}"


@pytest.mark.asyncio
async def test_run_generation_renders_uploads_and_sets_pdf_path() -> None:
    from generation.pipeline import GenerationPipeline

    provider = FakeProvider([CV_DRAFT, REVIEW_CLEAN, VERIFIER_OK])
    pipeline = GenerationPipeline(provider=provider, retriever=FakeRetrieverR())
    doc_repo = FakeDocumentRepo()
    job_repo = FakeJobRepo()
    profile_repo = FakeProfileRepo()
    profile_repo.upsert(USER_ID, {"name": "Lucas", "links": {}}, "raw")
    renderer = FakeRenderer()
    storage = FakePdfStorage()

    service = GenerationService(
        pipeline=pipeline,
        doc_repo=doc_repo,
        job_repo=job_repo,
        profile_repo=profile_repo,
        renderer=renderer,
        pdf_storage=storage,
    )
    job_id = job_repo.insert(
        USER_ID,
        {"source": "manual", "title": "ML Intern", "description": "Python." * 60, "status": "saved"},
    )["id"]
    row = service.start_generation(USER_ID, job_id, "cv")
    await service.run_generation(USER_ID, job_id, row["id"], "cv")

    stored = doc_repo.rows[row["id"]]
    assert stored["status"] == "complete"
    assert stored["pdf_path"] == f"{USER_ID}/{row['id']}.pdf"
    assert storage.uploads[stored["pdf_path"]] == b"%PDF-fake"
    assert renderer.calls[0]["doc_type"] == "cv"
    # signed URL flows through the service
    assert service.get_pdf_url(USER_ID, row["id"]).startswith("https://signed.example/")


@pytest.mark.asyncio
async def test_render_failure_keeps_document_complete_with_error() -> None:
    from generation.pipeline import GenerationPipeline

    class ExplodingRenderer:
        def render(self, *args, **kwargs):
            raise RuntimeError("typst binary missing")

    provider = FakeProvider([CV_DRAFT, REVIEW_CLEAN, VERIFIER_OK])
    pipeline = GenerationPipeline(provider=provider, retriever=FakeRetrieverR())
    doc_repo = FakeDocumentRepo()
    job_repo = FakeJobRepo()
    profile_repo = FakeProfileRepo()
    profile_repo.upsert(USER_ID, {"name": "Lucas", "links": {}}, "raw")

    service = GenerationService(
        pipeline=pipeline,
        doc_repo=doc_repo,
        job_repo=job_repo,
        profile_repo=profile_repo,
        renderer=ExplodingRenderer(),
        pdf_storage=FakePdfStorage(),
    )
    job_id = job_repo.insert(
        USER_ID,
        {"source": "manual", "title": "X", "description": "Y" * 500, "status": "saved"},
    )["id"]
    row = service.start_generation(USER_ID, job_id, "cv")
    await service.run_generation(USER_ID, job_id, row["id"], "cv")

    stored = doc_repo.rows[row["id"]]
    assert stored["status"] == "complete"  # content still usable
    assert "PDF rendering failed" in stored["error"]
    assert stored.get("pdf_path") is None
