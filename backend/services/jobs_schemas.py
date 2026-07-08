"""Pydantic schemas for job intake (Adzuna search + manual paste)."""

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, HttpUrl, model_validator

JobStatus = Literal["saved", "applied", "interview", "offer", "rejected"]
JOB_STATUSES: tuple[str, ...] = (
    "saved",
    "applied",
    "interview",
    "offer",
    "rejected",
)


class JobSearchResult(BaseModel):
    """One Adzuna hit, mapped to our shape."""

    adzuna_id: str
    title: str
    company: str | None = None
    location: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    snippet: str | None = None
    redirect_url: str | None = None


class JobSearchResponse(BaseModel):
    results: list[JobSearchResult]
    count: int | None = None
    page: int


class AdzunaJobCreate(BaseModel):
    """Save a job straight from an Adzuna search result payload."""

    source: Literal["adzuna"]
    payload: JobSearchResult
    description: str | None = Field(
        default=None, description="Full JD text if the user pasted it too."
    )


class ManualJobCreate(BaseModel):
    """Paste-a-job intake: description text, or a URL we politely fetch."""

    source: Literal["manual"]
    title: str = Field(min_length=1)
    company: str | None = None
    url: HttpUrl | None = None
    description: str | None = None

    @model_validator(mode="after")
    def require_description_or_url(self) -> "ManualJobCreate":
        if not self.description and not self.url:
            raise ValueError("Provide a job description or a URL.")
        return self


JobCreate = Annotated[
    Union[AdzunaJobCreate, ManualJobCreate], Field(discriminator="source")
]


class JobUpdate(BaseModel):
    """PATCH body — currently only kanban status changes."""

    status: JobStatus


class Job(BaseModel):
    """A saved job row."""

    id: str
    source: Literal["adzuna", "manual"]
    title: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    url: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    status: JobStatus = "saved"
    match_score: float | None = None
    skill_gaps: dict[str, Any] | list[Any] | None = None
    applied_at: str | None = None
    updated_at: str | None = None
    created_at: str | None = None
