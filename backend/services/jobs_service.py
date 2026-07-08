"""Job intake orchestration: Adzuna save + manual paste/URL intake, CRUD."""

from datetime import datetime, timezone
from typing import Any

from ingestion.url_extractor import extract_jd_from_url
from services.jobs_schemas import (
    AdzunaJobCreate,
    Job,
    ManualJobCreate,
)
from storage.repositories import JobRepositoryProtocol


class JobNotFoundError(Exception):
    """The requested job doesn't exist (or isn't owned by this user)."""


class JobsService:
    def __init__(self, repo: JobRepositoryProtocol) -> None:
        self._repo = repo

    async def save_adzuna_job(
        self, user_id: str, body: AdzunaJobCreate
    ) -> Job:
        p = body.payload
        row: dict[str, Any] = {
            "source": "adzuna",
            "title": p.title,
            "company": p.company,
            "location": p.location,
            "description": body.description or p.snippet,
            "url": p.redirect_url,
            "salary_min": p.salary_min,
            "salary_max": p.salary_max,
            "status": "saved",
        }
        return Job.model_validate(self._repo.insert(user_id, row))

    async def save_manual_job(
        self, user_id: str, body: ManualJobCreate
    ) -> Job:
        """Manual intake. If only a URL was given, politely fetch the JD.

        Raises UrlExtractionError (bubbled to the API layer) with clear
        paste-the-text-instead guidance when the fetch fails or is blocked.
        """
        description = body.description
        if not description and body.url is not None:
            description = await extract_jd_from_url(str(body.url))

        row: dict[str, Any] = {
            "source": "manual",
            "title": body.title,
            "company": body.company,
            "description": description,
            "url": str(body.url) if body.url else None,
            "status": "saved",
        }
        return Job.model_validate(self._repo.insert(user_id, row))

    def list_jobs(self, user_id: str, status: str | None = None) -> list[Job]:
        return [Job.model_validate(r) for r in self._repo.list(user_id, status)]

    def get_job(self, user_id: str, job_id: str) -> Job:
        row = self._repo.get(user_id, job_id)
        if row is None:
            raise JobNotFoundError(job_id)
        return Job.model_validate(row)

    def update_status(self, user_id: str, job_id: str, status: str) -> Job:
        fields: dict[str, Any] = {"status": status}
        if status == "applied":
            current = self._repo.get(user_id, job_id)
            if current is None:
                raise JobNotFoundError(job_id)
            # Auto-set once — moving a card back and forth keeps the
            # original application date (Prompt 8).
            if not current.get("applied_at"):
                fields["applied_at"] = datetime.now(
                    timezone.utc
                ).isoformat()
        row = self._repo.update(user_id, job_id, fields)
        if row is None:
            raise JobNotFoundError(job_id)
        return Job.model_validate(row)

    def delete_job(self, user_id: str, job_id: str) -> None:
        if not self._repo.delete(user_id, job_id):
            raise JobNotFoundError(job_id)
