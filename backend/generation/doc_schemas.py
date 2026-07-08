"""Pydantic models for the generation pipeline (Prompt 6).

One generic draft shape serves both doc types:
- cv: multiple sections, each unit is a bullet.
- cover_letter: exactly one section titled "letter", each unit a paragraph
  (exactly 4 paragraphs).
Every unit carries the profile-chunk ids that support it — the grounding
verifier audits those citations claim by claim.
"""

from typing import Literal

from pydantic import BaseModel, Field

DocType = Literal["cv", "cover_letter"]
DocumentStatus = Literal["pending", "complete", "failed"]


class DraftUnit(BaseModel):
    """One bullet (cv) or one paragraph (cover_letter)."""

    text: str
    chunk_ids: list[str] = Field(
        default_factory=list,
        description="Profile chunk ids that support this text.",
    )


class DraftSection(BaseModel):
    title: str
    units: list[DraftUnit]


class DraftDocument(BaseModel):
    doc_type: DocType
    sections: list[DraftSection]

    def all_units(self) -> list[DraftUnit]:
        return [u for s in self.sections for u in s.units]


class ReviewScores(BaseModel):
    """Reviewer rubric, each 0-100 (red_flags: 100 = no red flags)."""

    keyword_coverage: int = Field(ge=0, le=100)
    specificity: int = Field(ge=0, le=100)
    structure: int = Field(ge=0, le=100)
    tone: int = Field(ge=0, le=100)
    red_flags: int = Field(ge=0, le=100)


class ReviewResult(BaseModel):
    scores: ReviewScores
    mandatory_fixes: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ClaimCheck(BaseModel):
    """Verifier verdict for one numbered claim."""

    index: int = Field(ge=0)
    verdict: Literal["grounded", "unsupported"]
    note: str | None = None


class VerifierResult(BaseModel):
    checks: list[ClaimCheck]


class ClaimVerdict(BaseModel):
    """One line of the persisted grounding report."""

    claim: str
    chunk_ids: list[str]
    verdict: Literal["grounded", "unsupported"]
    note: str | None = None


class GroundingReport(BaseModel):
    claims: list[ClaimVerdict]
    grounding_rate: float = Field(ge=0, le=1)
    removed_claims: list[str] = Field(default_factory=list)


class GenerationResult(BaseModel):
    """What the pipeline returns to the service layer."""

    document: DraftDocument
    review: ReviewResult
    grounding: GroundingReport
