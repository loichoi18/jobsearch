"""Request/response models for the CV-enhance endpoint."""

from pydantic import BaseModel, Field


class EnhanceCvRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    resume: str = Field(min_length=1, max_length=40_000)
    job_description: str = Field(min_length=1, max_length=40_000)


class EnhanceCvResponse(BaseModel):
    result: str
