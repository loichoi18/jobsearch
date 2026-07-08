"""Prompt 9 tests: skill-gap aggregation (impact ordering, evidence), the
upskill-plan cache (hit while job set unchanged, invalidate on change)."""

import json
from typing import Any

import pytest

from services.insights_service import (
    InsightsService,
    aggregate_skill_gaps,
    job_set_fingerprint,
)
from tests.fakes import FakeJobRepo, FakeProfileRepo, FakeProvider

USER_ID = "11111111-2222-3333-4444-555555555555"


def gap_job(
    job_id: str,
    title: str,
    missing: list[dict[str, str]],
    company: str | None = "Acme",
) -> dict[str, Any]:
    return {
        "id": job_id,
        "user_id": USER_ID,
        "title": title,
        "company": company,
        "skill_gaps": {"missing_skills": missing},
    }


FIXTURE_JOBS = [
    gap_job(
        "j1",
        "ML Intern",
        [
            {"name": "Kubernetes", "importance": "required", "evidence": "must have k8s"},
            {"name": "Airflow", "importance": "preferred", "evidence": "airflow a plus"},
        ],
    ),
    gap_job(
        "j2",
        "AI Grad",
        [
            {"name": "kubernetes", "importance": "required", "evidence": "k8s essential"},
            {"name": "Spark", "importance": "required", "evidence": "spark required"},
        ],
    ),
    gap_job(
        "j3",
        "Data Intern",
        [
            {"name": "Airflow", "importance": "preferred", "evidence": "nice: airflow"},
        ],
    ),
    # Unanalyzed job must be excluded from denominators
    {"id": "j4", "user_id": USER_ID, "title": "No analysis", "skill_gaps": None},
]


# ------------------------------------------------------------- aggregation
def test_aggregation_impact_ordering_and_counts() -> None:
    result = aggregate_skill_gaps(FIXTURE_JOBS)
    assert result.jobs_analyzed == 3

    by_skill = {g.skill.lower(): g for g in result.gaps}
    k8s = by_skill["kubernetes"]
    assert k8s.frequency == 2
    assert k8s.required_count == 2
    assert k8s.impact == 4.0  # 2 jobs x required(2)
    assert k8s.pct_of_jobs == pytest.approx(2 / 3, abs=1e-3)

    airflow = by_skill["airflow"]
    assert airflow.impact == 2.0  # 2 jobs x preferred(1)
    spark = by_skill["spark"]
    assert spark.impact == 2.0  # 1 job x required(2)

    # Impact-sorted: kubernetes first
    assert result.gaps[0].skill.lower() == "kubernetes"
    # Evidence carries the exact JD phrases
    assert any("k8s" in e.phrase for e in k8s.evidence)


def test_aggregation_handles_no_jobs() -> None:
    result = aggregate_skill_gaps([])
    assert result.jobs_analyzed == 0
    assert result.gaps == []


def test_fingerprint_changes_with_job_set() -> None:
    fp1 = job_set_fingerprint(FIXTURE_JOBS)
    fp2 = job_set_fingerprint(FIXTURE_JOBS[:2])
    assert fp1 != fp2
    assert fp1 == job_set_fingerprint(list(reversed(FIXTURE_JOBS)))  # order-free


# ------------------------------------------------------------- plan + cache
VALID_PLAN = json.dumps(
    {
        "items": [
            {
                "skill": "Kubernetes",
                "why_it_matters": "Most target roles deploy on k8s.",
                "learning_path": "Week 1-2: official tutorial; week 3: deploy JobPilot backend.",
                "project_idea": "Containerise and deploy this project's API on a free k8s cluster.",
            }
        ]
    }
)


def make_service(
    responses: list[str],
) -> tuple[InsightsService, FakeJobRepo, FakeProvider]:
    provider = FakeProvider(responses)
    job_repo = FakeJobRepo()
    profile_repo = FakeProfileRepo()
    profile_repo.upsert(USER_ID, {"skills": {"technical": ["Python"]}}, "raw")
    service = InsightsService(
        job_repo=job_repo,
        profile_repo=profile_repo,
        provider=provider,
        plan_cache={},
    )
    return service, job_repo, provider


def seed(job_repo: FakeJobRepo, jobs: list[dict[str, Any]]) -> None:
    for j in jobs:
        row = {k: v for k, v in j.items() if k != "id"}
        job_repo.insert(USER_ID, row)


@pytest.mark.asyncio
async def test_upskill_plan_cached_until_job_set_changes() -> None:
    service, job_repo, provider = make_service([VALID_PLAN, VALID_PLAN])
    seed(job_repo, FIXTURE_JOBS[:2])

    first = await service.upskill_plan(USER_ID)
    second = await service.upskill_plan(USER_ID)
    assert first.items[0].skill == "Kubernetes"
    assert len(provider.calls) == 1  # second call served from cache

    # Adding an analyzed job invalidates the cache
    seed(job_repo, [FIXTURE_JOBS[2]])
    await service.upskill_plan(USER_ID)
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_upskill_plan_empty_when_no_gaps() -> None:
    service, _, provider = make_service([])
    plan = await service.upskill_plan(USER_ID)
    assert plan.items == []
    assert provider.calls == []  # no LLM call for nothing
