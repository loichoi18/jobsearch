"""Structured profile schema — the single source of truth for what a
profile looks like across ingestion, retrieval, and generation."""

from pydantic import BaseModel, Field


class EducationEntry(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    grade: str | None = None


class ExperienceEntry(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    tech: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)


class Skills(BaseModel):
    technical: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    name: str | None = None
    issuer: str | None = None
    year: str | None = None


class Profile(BaseModel):
    # Header/contact fields (Prompt 7: needed to render the CV header).
    # The extractor fills these from the CV text; null when absent.
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    # Preferred job locations (AU cities). Multi-select in the UI; used to
    # default the job search. The CV header falls back to the first of these
    # when `location` is empty.
    preferred_locations: list[str] = Field(default_factory=list)

    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    visa_status: str | None = None
    links: dict[str, str] = Field(default_factory=dict)
