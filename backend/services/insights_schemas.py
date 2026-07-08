"""Pydantic models for cross-job skill-gap insights (Prompt 9)."""

from pydantic import BaseModel, Field


class GapEvidence(BaseModel):
    job_id: str
    job_title: str
    company: str | None = None
    importance: str
    phrase: str


class SkillGapInsight(BaseModel):
    skill: str
    frequency: int = Field(description="Number of analyzed jobs demanding it.")
    pct_of_jobs: float = Field(ge=0, le=1)
    required_count: int
    preferred_count: int
    impact: float = Field(
        description="frequency x importance (required=2, preferred=1)."
    )
    evidence: list[GapEvidence] = Field(default_factory=list)


class SkillGapsResponse(BaseModel):
    jobs_analyzed: int
    gaps: list[SkillGapInsight]


class UpskillItem(BaseModel):
    skill: str
    why_it_matters: str
    learning_path: str = Field(
        description="A concrete 2-4 week plan with specific resources/steps."
    )
    project_idea: str = Field(
        description="A portfolio project that would evidence this skill."
    )


class UpskillPlan(BaseModel):
    items: list[UpskillItem]
