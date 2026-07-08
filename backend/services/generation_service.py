"""Document generation orchestration (Prompts 6 + 7).

Generation takes 30-60s on free-tier LLMs, so the flow is:
1. POST /generate creates a `pending` document row and schedules a
   background run — the response returns immediately with the document id.
2. The background run executes the pipeline, renders the PDF with Typst
   (CV: 2-page enforcement loop), uploads it to Supabase Storage, and
   updates the row to `complete` or `failed`.
3. The frontend polls GET /api/documents/{id} until it leaves `pending`.

Rendering is best-effort: a Typst/storage failure keeps the document
`complete` (content + grounding report are still useful) and records the
render error instead of failing the whole run.
"""

import json
import logging
from typing import Any

from generation.doc_schemas import DocType, DraftDocument
from generation.pipeline import GenerationPipeline
from generation.renderer import DocumentRenderer
from services.jobs_service import JobNotFoundError
from storage.pdf_storage import PdfStorageProtocol
from storage.repositories import (
    DocumentRepositoryProtocol,
    JobRepositoryProtocol,
    ProfileRepositoryProtocol,
)

logger = logging.getLogger(__name__)


class NoProfileError(RuntimeError):
    """User has no profile yet — generation needs one."""


class GenerationService:
    def __init__(
        self,
        pipeline: GenerationPipeline,
        doc_repo: DocumentRepositoryProtocol,
        job_repo: JobRepositoryProtocol,
        profile_repo: ProfileRepositoryProtocol,
        renderer: DocumentRenderer | None = None,
        pdf_storage: PdfStorageProtocol | None = None,
        signed_url_ttl_s: int = 300,
    ) -> None:
        self._pipeline = pipeline
        self._doc_repo = doc_repo
        self._job_repo = job_repo
        self._profile_repo = profile_repo
        self._renderer = renderer
        self._pdf_storage = pdf_storage
        self._signed_url_ttl_s = signed_url_ttl_s

    def start_generation(
        self, user_id: str, job_id: str, doc_type: DocType
    ) -> dict[str, Any]:
        """Validate inputs and create the pending document row."""
        job = self._job_repo.get(user_id, job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        if self._profile_repo.get(user_id) is None:
            raise NoProfileError(
                "No profile yet — upload your CV before generating documents."
            )
        version = self._doc_repo.next_version(user_id, job_id, doc_type)
        return self._doc_repo.insert(
            user_id,
            {
                "job_id": job_id,
                "doc_type": doc_type,
                "version": version,
                "status": "pending",
            },
        )

    async def run_generation(
        self, user_id: str, job_id: str, doc_id: str, doc_type: DocType
    ) -> None:
        """Background task: run the pipeline, persist outcome. Never raises."""
        try:
            job = self._job_repo.get(user_id, job_id)
            profile_row = self._profile_repo.get(user_id)
            if job is None or profile_row is None:
                raise RuntimeError("Job or profile disappeared mid-run.")

            jd_text = job.get("description") or job.get("title") or ""
            result = await self._pipeline.generate(
                user_id=user_id,
                doc_type=doc_type,
                jd_text=jd_text,
                structured_profile=profile_row["structured"],
            )

            fields: dict[str, Any] = {
                "typst_source": result.document.model_dump_json(),
                "grounding_report": result.grounding.model_dump(),
                "status": "complete",
                "error": None,
            }

            render_error = self._render_and_upload(
                user_id=user_id,
                job_id=job_id,
                doc_id=doc_id,
                document=result.document,
                structured_profile=profile_row["structured"],
                jd_text=jd_text,
                fields=fields,
            )
            if render_error:
                fields["error"] = render_error

            self._doc_repo.update(user_id, doc_id, fields)
        except Exception as exc:  # noqa: BLE001 — background task must not raise
            logger.exception("Generation failed for document %s", doc_id)
            self._doc_repo.update(
                user_id,
                doc_id,
                {"status": "failed", "error": str(exc)[:500]},
            )

    def _render_and_upload(
        self,
        user_id: str,
        job_id: str,
        doc_id: str,
        document: DraftDocument,
        structured_profile: dict[str, Any],
        jd_text: str,
        fields: dict[str, Any],
    ) -> str | None:
        """Render + upload the PDF. Returns an error message on failure."""
        if self._renderer is None or self._pdf_storage is None:
            return None
        try:
            cl_chunk_ids = (
                self._cover_letter_chunk_ids(user_id, job_id)
                if document.doc_type == "cv"
                else frozenset()
            )
            outcome = self._renderer.render(
                document=document,
                structured_profile=structured_profile,
                jd_text=jd_text,
                cover_letter_chunk_ids=cl_chunk_ids,
            )
            path = f"{user_id}/{doc_id}.pdf"
            self._pdf_storage.upload(path, outcome.pdf_bytes)
            fields["pdf_path"] = path
            # The cutting loop may have trimmed the CV — persist what rendered.
            fields["typst_source"] = outcome.document.model_dump_json()
            if outcome.cut_bullets:
                logger.info(
                    "2-page limit: cut %d bullets from %s",
                    len(outcome.cut_bullets),
                    doc_id,
                )
            return None
        except Exception as exc:  # noqa: BLE001 — render failure is non-fatal
            logger.exception("PDF render/upload failed for %s", doc_id)
            return f"PDF rendering failed: {str(exc)[:300]}"

    def _cover_letter_chunk_ids(
        self, user_id: str, job_id: str
    ) -> frozenset[str]:
        """Chunk ids cited by the latest complete cover letter for this job."""
        summaries = self._doc_repo.list_for_job(user_id, job_id)
        letters = [
            s
            for s in summaries
            if s["doc_type"] == "cover_letter" and s.get("status") == "complete"
        ]
        if not letters:
            return frozenset()
        latest = max(letters, key=lambda s: s.get("version", 0))
        row = self._doc_repo.get(user_id, latest["id"])
        if not row or not row.get("typst_source"):
            return frozenset()
        try:
            letter = DraftDocument.model_validate(
                json.loads(row["typst_source"])
            )
        except Exception:  # noqa: BLE001 — malformed old rows are ignorable
            return frozenset()
        return frozenset(
            cid for unit in letter.all_units() for cid in unit.chunk_ids
        )

    def get_document(self, user_id: str, doc_id: str) -> dict[str, Any] | None:
        return self._doc_repo.get(user_id, doc_id)

    def get_pdf_url(self, user_id: str, doc_id: str) -> str | None:
        """Short-lived signed URL for the rendered PDF, or None."""
        row = self._doc_repo.get(user_id, doc_id)
        if not row or not row.get("pdf_path") or self._pdf_storage is None:
            return None
        return self._pdf_storage.signed_url(
            row["pdf_path"], self._signed_url_ttl_s
        )

    def list_documents(
        self, user_id: str, job_id: str
    ) -> list[dict[str, Any]]:
        return self._doc_repo.list_for_job(user_id, job_id)
