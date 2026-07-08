"""Cross-job skill-gap aggregation + LLM upskill plan (Prompt 9).

Aggregation is pure Python over jobs.skill_gaps (jsonb). The upskill plan is
one LLM call over the top gaps + a profile summary, cached in-process until
the user's analyzed-job set changes (fingerprint over job ids + gap names).
"""

import hashlib
import json
from collections import defaultdict
from typing import Any

from pydantic import ValidationError

from generation.provider import LLMProvider
from services.insights_schemas import (
    GapEvidence,
    SkillGapInsight,
    SkillGapsResponse,
    UpskillItem,
    UpskillPlan,
)
from storage.repositories import (
    JobRepositoryProtocol,
    ProfileRepositoryProtocol,
)

IMPORTANCE_WEIGHT = {"required": 2, "preferred": 1}
MAX_EVIDENCE_PER_SKILL = 3
TOP_GAPS_FOR_PLAN = 10


class UpskillPlanError(RuntimeError):
    """LLM plan output invalid after one retry."""


UPSKILL_SYSTEM_PROMPT = """You are a pragmatic career mentor for an \
Australian AI/ML student. For each skill gap, produce:
- why_it_matters: 1-2 frank sentences tied to the target roles.
- learning_path: a concrete 2-4 week plan. Name specific, real resources
  (official docs, well-known courses) and weekly milestones. No fluff.
- project_idea: ONE specific portfolio project that would evidence the skill,
  scoped to be finishable, described in 1-2 sentences. It should build on the
  student's existing profile where possible, not start from zero.
Be specific, not generic. Never recommend padding a CV with unlearned skills.
"""


def aggregate_skill_gaps(jobs: list[dict[str, Any]]) -> SkillGapsResponse:
    """Aggregate missing_skills across analyzed jobs; sort by impact."""
    analyzed = [j for j in jobs if isinstance(j.get("skill_gaps"), dict)]
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "display": "",
            "jobs": set(),
            "required": 0,
            "preferred": 0,
            "evidence": [],
        }
    )

    for job in analyzed:
        missing = job["skill_gaps"].get("missing_skills") or []
        seen_in_job: set[str] = set()
        for item in missing:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            b = buckets[key]
            b["display"] = b["display"] or name
            importance = (
                item.get("importance")
                if item.get("importance") in IMPORTANCE_WEIGHT
                else "preferred"
            )
            # Count each skill once per job for frequency purposes
            if key not in seen_in_job:
                b["jobs"].add(job["id"])
                b[importance] += 1
                seen_in_job.add(key)
            if len(b["evidence"]) < MAX_EVIDENCE_PER_SKILL:
                b["evidence"].append(
                    GapEvidence(
                        job_id=str(job["id"]),
                        job_title=job.get("title") or "",
                        company=job.get("company"),
                        importance=importance,
                        phrase=item.get("evidence") or "",
                    )
                )

    total = len(analyzed)
    gaps: list[SkillGapInsight] = []
    for b in buckets.values():
        frequency = len(b["jobs"])
        weight_sum = 2 * b["required"] + 1 * b["preferred"]
        gaps.append(
            SkillGapInsight(
                skill=b["display"],
                frequency=frequency,
                pct_of_jobs=round(frequency / total, 4) if total else 0.0,
                required_count=b["required"],
                preferred_count=b["preferred"],
                # impact = frequency x avg importance == summed weights
                impact=float(weight_sum),
                evidence=b["evidence"],
            )
        )
    gaps.sort(key=lambda g: (-g.impact, -g.frequency, g.skill.lower()))
    return SkillGapsResponse(jobs_analyzed=total, gaps=gaps)


def job_set_fingerprint(jobs: list[dict[str, Any]]) -> str:
    """Changes whenever the analyzed-job set or its gaps change."""
    parts = sorted(
        f"{j['id']}:{json.dumps(j.get('skill_gaps'), sort_keys=True, default=str)}"
        for j in jobs
        if isinstance(j.get("skill_gaps"), dict)
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


class InsightsService:
    def __init__(
        self,
        job_repo: JobRepositoryProtocol,
        profile_repo: ProfileRepositoryProtocol,
        provider: LLMProvider,
        plan_cache: dict[str, tuple[str, UpskillPlan]] | None = None,
    ) -> None:
        self._job_repo = job_repo
        self._profile_repo = profile_repo
        self._provider = provider
        # user_id -> (fingerprint, plan). Process-local: fine for free tier.
        self._plan_cache = plan_cache if plan_cache is not None else {}

    def skill_gaps(self, user_id: str) -> SkillGapsResponse:
        return aggregate_skill_gaps(self._job_repo.list(user_id))

    async def upskill_plan(self, user_id: str) -> UpskillPlan:
        jobs = self._job_repo.list(user_id)
        fingerprint = job_set_fingerprint(jobs)
        cached = self._plan_cache.get(user_id)
        if cached and cached[0] == fingerprint:
            return cached[1]

        gaps = aggregate_skill_gaps(jobs).gaps[:TOP_GAPS_FOR_PLAN]
        if not gaps:
            plan = UpskillPlan(items=[])
            self._plan_cache[user_id] = (fingerprint, plan)
            return plan

        plan = await self._generate_plan(user_id, gaps)
        self._plan_cache[user_id] = (fingerprint, plan)
        return plan

    async def _generate_plan(self, user_id: str, gaps: list) -> UpskillPlan:
        profile_row = self._profile_repo.get(user_id)
        structured = (profile_row or {}).get("structured") or {}
        profile_summary = {
            "skills": structured.get("skills"),
            "projects": [
                {"name": p.get("name"), "tech": p.get("tech")}
                for p in structured.get("projects") or []
            ],
            "education": [
                {"degree": e.get("degree"), "field": e.get("field")}
                for e in structured.get("education") or []
            ],
        }
        gaps_payload = [
            {
                "skill": g.skill,
                "required_count": g.required_count,
                "preferred_count": g.preferred_count,
                "example_jd_phrases": [e.phrase for e in g.evidence],
            }
            for g in gaps
        ]
        user_prompt = (
            f"STUDENT PROFILE SUMMARY:\n{json.dumps(profile_summary)}\n\n"
            f"TOP SKILL GAPS ACROSS SAVED JOBS:\n{json.dumps(gaps_payload)}\n\n"
            "Produce the upskill plan JSON (one item per gap, same order)."
        )
        schema = UpskillPlan.model_json_schema()
        response = await self._provider.complete(
            system=UPSKILL_SYSTEM_PROMPT, user=user_prompt, json_schema=schema
        )
        try:
            return UpskillPlan.model_validate(json.loads(response))
        except (json.JSONDecodeError, ValidationError) as first_error:
            retry = (
                f"{user_prompt}\n\nYour previous output was invalid:\n"
                f"{first_error}\nReturn corrected JSON."
            )
            response = await self._provider.complete(
                system=UPSKILL_SYSTEM_PROMPT, user=retry, json_schema=schema
            )
            try:
                return UpskillPlan.model_validate(json.loads(response))
            except (json.JSONDecodeError, ValidationError) as second_error:
                raise UpskillPlanError(
                    f"Upskill plan failed after retry: {second_error}"
                ) from second_error


# Module-level cache shared across requests in this process.
_PLAN_CACHE: dict[str, tuple[str, UpskillPlan]] = {}


def get_shared_plan_cache() -> dict[str, tuple[str, UpskillPlan]]:
    return _PLAN_CACHE
