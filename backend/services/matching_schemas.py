"""Pydantic models for match scoring and skill-gap extraction (Prompt 5)."""

from typing import Literal

from pydantic import BaseModel, Field

SkillImportance = Literal["required", "preferred"]


class CriterionBreakdown(BaseModel):
    """Per-criterion rubric scores, each 0-100."""

    technical_skills: int = Field(ge=0, le=100)
    experience_relevance: int = Field(ge=0, le=100)
    education_fit: int = Field(ge=0, le=100)
    nice_to_haves: int = Field(ge=0, le=100)


class MissingSkill(BaseModel):
    name: str
    importance: SkillImportance
    evidence: str = Field(
        description="The exact JD phrase demanding this skill."
    )


class RubricResult(BaseModel):
    """What the LLM returns for the rubric evaluation."""

    rubric_score: int = Field(ge=0, le=100)
    breakdown: CriterionBreakdown
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[MissingSkill] = Field(default_factory=list)
    one_line_verdict: str


class MatchAnalysis(BaseModel):
    """Full analysis persisted to jobs.skill_gaps (jsonb) + jobs.match_score."""

    match_score: float = Field(ge=0, le=100)
    semantic_score: float = Field(ge=0, le=1)
    rubric_score: int = Field(ge=0, le=100)
    breakdown: CriterionBreakdown
    matched_skills: list[str]
    missing_skills: list[MissingSkill]
    one_line_verdict: str
    short_description: bool = Field(
        default=False,
        description=(
            "True when the stored JD is suspiciously short (e.g. an Adzuna "
            "snippet) — scores will be unreliable; paste the full JD."
        ),
    )
