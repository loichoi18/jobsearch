"""Prompt 11 tests: metric math and the fabrication-trap logic.

These run against the deterministic MockProvider + in-memory retriever, so no
network, no database, no Typst — the same path CI uses with `--mock`.
"""

import json

from evaluation import metrics
from evaluation.harness import aggregate, load_dataset, run_case
from evaluation.mock import (
    InMemoryRetriever,
    MockProvider,
    profile_to_chunks,
)
from evaluation.schemas import CaseResult, EvalCase
from generation.doc_schemas import DraftDocument
from generation.pipeline import GenerationPipeline

REFERENCE_PROFILE = {
    "skills": {"technical": ["Python", "PyTorch"], "tools": ["FastAPI"]},
    "projects": [
        {
            "name": "LLM Eval Harness",
            "description": "Grounding-rate evaluation.",
            "tech": ["Python"],
            "outcomes": ["Automated grounding checks"],
        }
    ],
}


# ------------------------------------------------------- pure metric math
def test_contains_term_is_word_boundary_aware() -> None:
    # "Go" must NOT match inside "good" or "category" — else the fabrication
    # metric would fire on innocent text.
    assert metrics.contains_term("I write good code in categories", "Go") is False
    assert metrics.contains_term("We use Go for services", "Go") is True
    assert metrics.contains_term("Built with Next.js today", "Next.js") is True


def test_keyword_coverage_counts_present_and_missing() -> None:
    text = "I use Python and FastAPI daily."
    rate, missing = metrics.keyword_coverage(
        ["Python", "FastAPI", "Kubernetes"], text
    )
    assert rate == 2 / 3
    assert missing == ["Kubernetes"]


def test_keyword_coverage_empty_is_full() -> None:
    assert metrics.keyword_coverage([], "anything") == (1.0, [])


def test_fabrication_rate_detects_leaks() -> None:
    text = "I am experienced with Kubernetes and Go."
    rate, leaked = metrics.fabrication_rate(["Kubernetes", "Go", "Rust"], text)
    assert rate == 2 / 3
    assert set(leaked) == {"Kubernetes", "Go"}


def test_fabrication_rate_zero_when_clean() -> None:
    rate, leaked = metrics.fabrication_rate(["Kubernetes"], "Only Python here.")
    assert rate == 0.0
    assert leaked == []


def test_estimate_pages_and_compliance() -> None:
    doc = DraftDocument.model_validate(
        {
            "doc_type": "cv",
            "sections": [
                {"title": "s", "units": [{"text": "word " * 600, "chunk_ids": []}]}
            ],
        }
    )
    assert metrics.estimate_pages(doc) == 2  # 600 words -> 2 pages @500/page
    assert metrics.length_compliant(2, 2) is True
    assert metrics.length_compliant(3, 2) is False
    assert metrics.length_compliant(None, 1) is True  # unknown -> not penalised


def test_cost_estimate_scales_with_rate() -> None:
    tokens = metrics.estimate_tokens(4000)  # 1000 tokens
    assert tokens == 1000
    assert metrics.estimate_cost_usd(tokens, 0.0) == 0.0
    # 1000 tokens at $3 per 1k tokens = $3.00
    assert metrics.estimate_cost_usd(tokens, 3.0) == 3.0
    # A realistic per-1k rate (e.g. $0.003) yields $0.003 for 1k tokens
    assert metrics.estimate_cost_usd(tokens, 0.003) == 0.003


# --------------------------------------------------- fabrication trap E2E
def _pipeline_for(case: EvalCase, leak: bool) -> GenerationPipeline:
    chunks = profile_to_chunks(REFERENCE_PROFILE)
    provider = MockProvider(case, chunks, leak_forbidden=leak)
    return GenerationPipeline(provider=provider, retriever=InMemoryRetriever(chunks))  # type: ignore[arg-type]


CASE = EvalCase(
    id="trap",
    title="ML Intern",
    jd_text="We need Kubernetes and Python for our platform.",
    expected_keywords=["Python"],
    forbidden_claims=["Kubernetes"],
    max_pages=1,
)


async def test_good_pipeline_never_fabricates() -> None:
    pipeline = _pipeline_for(CASE, leak=False)
    result = await pipeline.generate("eval", "cover_letter", CASE.jd_text, REFERENCE_PROFILE)
    text = metrics.document_text(result.document)
    rate, leaked = metrics.fabrication_rate(CASE.forbidden_claims, text)
    assert rate == 0.0
    assert leaked == []
    assert result.grounding.grounding_rate == 1.0


async def test_fabrication_trap_is_caught_when_mock_leaks() -> None:
    # A deliberately bad generation must be measured as a fabrication — this is
    # the guardrail that would fail CI on a real regression.
    pipeline = _pipeline_for(CASE, leak=True)
    result = await pipeline.generate("eval", "cover_letter", CASE.jd_text, REFERENCE_PROFILE)
    text = metrics.document_text(result.document)
    rate, leaked = metrics.fabrication_rate(CASE.forbidden_claims, text)
    assert rate == 1.0
    assert leaked == ["Kubernetes"]


async def test_run_case_produces_clean_metrics() -> None:
    case = load_dataset("v1").cases[0]
    profile = json.loads(
        (
            __import__("pathlib").Path(
                "evaluation/dataset/reference_profile.json"
            ).read_text(encoding="utf-8")
        )
    )
    result = await run_case(case, profile, mock=True, cost_per_1k=0.0)
    assert isinstance(result, CaseResult)
    assert result.error is None
    assert result.fabrication_rate == 0.0
    assert result.grounding_rate == 1.0
    assert result.est_tokens > 0


# --------------------------------------------------------- aggregate math
def test_aggregate_averages_and_counts_errors() -> None:
    results = [
        CaseResult(
            case_id="a", title="A", doc_type="cover_letter", grounding_rate=1.0,
            fabrication_rate=0.0, keyword_coverage=1.0, length_compliant=True,
            latency_s=0.1, est_tokens=100, est_cost_usd=0.0,
        ),
        CaseResult(
            case_id="b", title="B", doc_type="cover_letter", grounding_rate=0.8,
            fabrication_rate=0.0, keyword_coverage=0.5, length_compliant=False,
            latency_s=0.3, est_tokens=200, est_cost_usd=0.0,
        ),
        CaseResult(
            case_id="c", title="C", doc_type="cv", grounding_rate=0.0,
            fabrication_rate=1.0, keyword_coverage=0.0, length_compliant=False,
            latency_s=0.2, est_tokens=0, est_cost_usd=0.0, error="boom",
        ),
    ]
    agg = aggregate(results)
    assert agg.cases == 3
    assert agg.errors == 1
    # Averages exclude the errored case
    assert agg.grounding_rate == 0.9
    assert agg.keyword_coverage == 0.75
    assert agg.length_compliance == 0.5
    assert agg.total_est_tokens == 300
