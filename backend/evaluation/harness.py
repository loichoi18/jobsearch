"""Evaluation harness (Prompt 11) — the differentiator.

Runs the real generation pipeline over a golden dataset and measures grounding
rate, fabrication rate (the fabrication trap), keyword coverage, length
compliance, latency, and an estimated token/cost figure. Aggregates a run
report, writes a markdown report, and optionally persists to eval_runs.

CLI:
    python -m evaluation.harness --dataset v1 [--cases N] [--mock]
                                 [--persist] [--cost-per-1k 0.0]

`--mock` swaps in a deterministic provider + in-memory retriever so CI runs for
free and yields identical numbers every time.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generation.pipeline import GenerationPipeline

from evaluation import metrics
from evaluation.mock import (
    InMemoryRetriever,
    MockProvider,
    RecordingProvider,
    profile_to_chunks,
)
from evaluation.schemas import (
    CaseResult,
    EvalCase,
    GoldenDataset,
    RunAggregate,
    RunReport,
)

DATASET_DIR = Path(__file__).parent / "dataset"
REPORTS_DIR = Path(__file__).parent / "reports"
DEFAULT_USD_PER_1K = 0.0  # Gemini free tier; set >0 to model the Claude swap


def load_dataset(version: str) -> GoldenDataset:
    path = DATASET_DIR / f"{version}.json"
    return GoldenDataset.model_validate_json(path.read_text(encoding="utf-8"))


def load_reference_profile() -> dict[str, Any]:
    path = DATASET_DIR / "reference_profile.json"
    return json.loads(path.read_text(encoding="utf-8"))


async def run_case(
    case: EvalCase,
    profile: dict[str, Any],
    *,
    mock: bool,
    cost_per_1k: float,
) -> CaseResult:
    """Run one case through the full pipeline and measure it."""
    chunks = profile_to_chunks(profile)
    retriever = InMemoryRetriever(chunks)

    if mock:
        base = MockProvider(case, chunks)
    else:
        from generation.provider import get_provider  # real Gemini call

        base = get_provider()

    recorder = RecordingProvider(base)
    pipeline = GenerationPipeline(provider=recorder, retriever=retriever)  # type: ignore[arg-type]

    start = time.perf_counter()
    try:
        result = await pipeline.generate(
            user_id="eval",
            doc_type=case.doc_type,
            jd_text=case.jd_text,
            structured_profile=profile,
        )
    except Exception as exc:  # noqa: BLE001 — one bad case must not abort the run
        latency = time.perf_counter() - start
        return CaseResult(
            case_id=case.id,
            title=case.title,
            doc_type=case.doc_type,
            grounding_rate=0.0,
            fabrication_rate=1.0,
            keyword_coverage=0.0,
            length_compliant=False,
            latency_s=round(latency, 3),
            est_tokens=0,
            est_cost_usd=0.0,
            error=str(exc)[:300],
        )
    latency = time.perf_counter() - start

    text = metrics.document_text(result.document)
    coverage, missing = metrics.keyword_coverage(case.expected_keywords, text)
    fab_rate, leaked = metrics.fabrication_rate(case.forbidden_claims, text)
    pages = metrics.estimate_pages(result.document)
    tokens = metrics.estimate_tokens(recorder.total_chars)

    return CaseResult(
        case_id=case.id,
        title=case.title,
        doc_type=case.doc_type,
        grounding_rate=result.grounding.grounding_rate,
        fabrication_rate=fab_rate,
        keyword_coverage=round(coverage, 4),
        leaked_claims=leaked,
        missing_keywords=missing,
        pages=pages,
        length_compliant=metrics.length_compliant(pages, case.max_pages),
        latency_s=round(latency, 3),
        est_tokens=tokens,
        est_cost_usd=metrics.estimate_cost_usd(tokens, cost_per_1k),
    )


def aggregate(results: list[CaseResult]) -> RunAggregate:
    n = len(results)
    ok = [r for r in results if r.error is None]

    def mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    return RunAggregate(
        cases=n,
        grounding_rate=mean([r.grounding_rate for r in ok]),
        fabrication_rate=mean([r.fabrication_rate for r in ok]),
        keyword_coverage=mean([r.keyword_coverage for r in ok]),
        length_compliance=mean([1.0 if r.length_compliant else 0.0 for r in ok]),
        avg_latency_s=mean([r.latency_s for r in results]),
        total_est_tokens=sum(r.est_tokens for r in results),
        total_est_cost_usd=round(sum(r.est_cost_usd for r in results), 6),
        errors=n - len(ok),
    )


async def run_dataset(
    version: str,
    *,
    cases: int | None = None,
    mock: bool = False,
    cost_per_1k: float = DEFAULT_USD_PER_1K,
) -> RunReport:
    dataset = load_dataset(version)
    profile = load_reference_profile()
    selected = dataset.cases[:cases] if cases else dataset.cases

    results: list[CaseResult] = []
    for case in selected:
        results.append(
            await run_case(case, profile, mock=mock, cost_per_1k=cost_per_1k)
        )

    return RunReport(
        dataset_version=version,
        mock=mock,
        aggregate=aggregate(results),
        cases=results,
    )


# ------------------------------------------------------------- reporting
def render_markdown(report: RunReport) -> str:
    a = report.aggregate
    lines = [
        f"# Eval run — dataset `{report.dataset_version}`"
        f"{' (mock)' if report.mock else ''}",
        "",
        f"_Generated {report.created_at}_",
        "",
        "## Aggregate",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Cases | {a.cases} |",
        f"| Grounding rate | {a.grounding_rate:.1%} |",
        f"| Fabrication rate | {a.fabrication_rate:.1%} |",
        f"| Keyword coverage | {a.keyword_coverage:.1%} |",
        f"| Length compliance | {a.length_compliance:.1%} |",
        f"| Avg latency | {a.avg_latency_s:.2f}s |",
        f"| Est. tokens | {a.total_est_tokens:,} |",
        f"| Est. cost | ${a.total_est_cost_usd:.4f} |",
        f"| Errors | {a.errors} |",
        "",
        "## Per case",
        "",
        "| Case | Type | Ground | Fabric | Keywords | Pages | Leaked |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in report.cases:
        leaked = ", ".join(r.leaked_claims) if r.leaked_claims else "—"
        pages = "—" if r.pages is None else str(r.pages)
        flag = " ⚠️" if (r.fabrication_rate > 0 or r.error) else ""
        lines.append(
            f"| {r.case_id}{flag} | {r.doc_type} | {r.grounding_rate:.0%} | "
            f"{r.fabrication_rate:.0%} | {r.keyword_coverage:.0%} | {pages} | {leaked} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_reports(report: RunReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    md_path = REPORTS_DIR / f"{report.dataset_version}_{stamp}.md"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (REPORTS_DIR / "latest.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    (REPORTS_DIR / "latest.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    return md_path


def persist_run(report: RunReport) -> None:
    """Insert the run into eval_runs (real mode only; imports Supabase lazily)."""
    from storage.repositories import EvalRunRepository
    from storage.supabase_client import get_supabase

    repo = EvalRunRepository(get_supabase())
    repo.insert(report.dataset_version, report.model_dump(mode="json"))


# ------------------------------------------------------------------ CLI
def main() -> int:
    parser = argparse.ArgumentParser(description="JobPilot AU eval harness")
    parser.add_argument("--dataset", default="v1")
    parser.add_argument("--cases", type=int, default=None)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--cost-per-1k", type=float, default=DEFAULT_USD_PER_1K)
    # CI gates (defaults mirror the GitHub Action)
    parser.add_argument("--min-grounding", type=float, default=0.0)
    parser.add_argument("--max-fabrication", type=float, default=1.0)
    args = parser.parse_args()

    report = asyncio.run(
        run_dataset(
            args.dataset,
            cases=args.cases,
            mock=args.mock,
            cost_per_1k=args.cost_per_1k,
        )
    )
    md_path = write_reports(report)
    print(render_markdown(report))
    print(f"\nReport written to {md_path}")

    if args.persist:
        persist_run(report)
        print("Run persisted to eval_runs.")

    a = report.aggregate
    if a.fabrication_rate > args.max_fabrication:
        print(
            f"\nFAIL: fabrication rate {a.fabrication_rate:.1%} exceeds "
            f"{args.max_fabrication:.1%}"
        )
        return 1
    if a.grounding_rate < args.min_grounding:
        print(
            f"\nFAIL: grounding rate {a.grounding_rate:.1%} below "
            f"{args.min_grounding:.1%}"
        )
        return 1
    if a.errors:
        print(f"\nFAIL: {a.errors} case(s) errored")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
