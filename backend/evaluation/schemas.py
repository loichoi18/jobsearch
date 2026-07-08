"""Pydantic models for the evaluation layer (Prompt 11).

The golden dataset is (JD, reference-profile) pairs with expectations that a
GOOD generation must satisfy: keywords it should surface, forbidden claims it
must NOT fabricate (skills the JD demands but the reference profile lacks — the
fabrication trap), and a page ceiling. The harness turns each case into a
CaseResult, then aggregates a RunReport that is persisted and rendered to
markdown.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from generation.doc_schemas import DocType


class EvalCase(BaseModel):
    """One golden-dataset case."""

    id: str
    title: str
    company: str = "Anonymized"
    doc_type: DocType = "cover_letter"
    jd_text: str
    expected_keywords: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(
        default_factory=list,
        description="Skills the JD demands but the reference profile lacks. "
        "None of these may appear in a grounded output.",
    )
    max_pages: int = 2
    # Marks cases whose jd_text is a realistic stand-in to be replaced with a
    # real anonymized posting. Purely informational; the case still runs.
    placeholder: bool = False


class GoldenDataset(BaseModel):
    version: str
    notes: str = ""
    cases: list[EvalCase]


class CaseResult(BaseModel):
    """Per-case metrics produced by the harness."""

    case_id: str
    title: str
    doc_type: DocType
    grounding_rate: float
    fabrication_rate: float
    keyword_coverage: float
    leaked_claims: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    pages: int | None = None
    length_compliant: bool
    latency_s: float
    est_tokens: int
    est_cost_usd: float
    error: str | None = None


class RunAggregate(BaseModel):
    """Dataset-level aggregate metrics (the README headline numbers)."""

    cases: int
    grounding_rate: float
    fabrication_rate: float
    keyword_coverage: float
    length_compliance: float
    avg_latency_s: float
    total_est_tokens: int
    total_est_cost_usd: float
    errors: int


class RunReport(BaseModel):
    """A full harness run: what gets persisted to eval_runs.metrics."""

    dataset_version: str
    mock: bool
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    aggregate: RunAggregate
    cases: list[CaseResult]
