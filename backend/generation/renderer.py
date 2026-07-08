"""Typst PDF rendering (Prompt 7).

The structured document JSON is written to a temp dir next to a copy of the
template, then the typst binary compiles it. Page count comes from pypdf.
CV rendering enforces the 2-page limit via relevance-weighted cutting
(generation/cutting.py): cut the lowest-scoring bullet, re-render, repeat
(max 10 iterations, then log and accept).
"""

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

from pypdf import PdfReader

from generation.cutting import cut_lowest_bullet
from generation.doc_schemas import DraftDocument

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
MAX_PAGES_CV = 2
MAX_CUT_ITERATIONS = 10
COMPILE_TIMEOUT_S = 30


class RenderError(RuntimeError):
    """Typst compilation failed."""


@dataclass
class RenderOutcome:
    pdf_bytes: bytes
    pages: int
    document: DraftDocument
    cut_bullets: list[str] = field(default_factory=list)


def build_header(structured_profile: dict[str, Any]) -> dict[str, str]:
    """Header/contact data for the templates, from the structured profile."""
    location = structured_profile.get("location") or next(
        iter(structured_profile.get("preferred_locations") or []), None
    )
    parts = [
        structured_profile.get("email"),
        structured_profile.get("phone"),
        location,
        *(structured_profile.get("links") or {}).values(),
    ]
    return {
        "name": structured_profile.get("name") or "",
        "contact_line": " · ".join(p for p in parts if p),
    }


def _document_to_template_data(
    document: DraftDocument, header: dict[str, str]
) -> dict[str, Any]:
    if document.doc_type == "cv":
        return {
            **header,
            "sections": [
                {
                    "title": s.title,
                    "units": [{"text": u.text} for u in s.units],
                }
                for s in document.sections
            ],
        }
    paragraphs = [u.text for u in document.all_units()]
    return {**header, "recipient_line": "", "paragraphs": paragraphs}


def compile_typst(
    document: DraftDocument,
    header: dict[str, str],
    typst_bin: str,
) -> tuple[bytes, int]:
    """One compile: returns (pdf_bytes, page_count)."""
    import json as _json

    template = TEMPLATES_DIR / f"{document.doc_type}.typ"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copy(template, tmp_path / "main.typ")
        (tmp_path / "data.json").write_text(
            _json.dumps(_document_to_template_data(document, header)),
            encoding="utf-8",
        )
        result = subprocess.run(
            [typst_bin, "compile", "main.typ", "out.pdf"],
            cwd=tmp_path,
            capture_output=True,
            timeout=COMPILE_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise RenderError(
                f"typst compile failed: {result.stderr.decode(errors='replace')[:800]}"
            )
        pdf_bytes = (tmp_path / "out.pdf").read_bytes()

    pages = len(PdfReader(BytesIO(pdf_bytes)).pages)
    return pdf_bytes, pages


RenderFn = Callable[[DraftDocument], tuple[bytes, int]]


def enforce_page_limit(
    document: DraftDocument,
    render_fn: RenderFn,
    jd_text: str,
    cover_letter_chunk_ids: frozenset[str] = frozenset(),
    max_pages: int = MAX_PAGES_CV,
    max_iterations: int = MAX_CUT_ITERATIONS,
) -> RenderOutcome:
    """Render; while too long, cut the lowest-scoring bullet and re-render.

    Pure control loop — render_fn is injected so the loop is unit-testable
    without the typst binary.
    """
    cut_bullets: list[str] = []
    pdf_bytes, pages = render_fn(document)
    iterations = 0
    while pages > max_pages and iterations < max_iterations:
        document, cut_text = cut_lowest_bullet(
            document, jd_text, cover_letter_chunk_ids
        )
        if cut_text is None:
            logger.warning("Nothing left to cut; accepting %d pages", pages)
            break
        cut_bullets.append(cut_text)
        pdf_bytes, pages = render_fn(document)
        iterations += 1

    if pages > max_pages:
        logger.warning(
            "CV still %d pages after %d cuts — accepting.", pages, iterations
        )
    return RenderOutcome(
        pdf_bytes=pdf_bytes,
        pages=pages,
        document=document,
        cut_bullets=cut_bullets,
    )


class DocumentRenderer:
    """What the generation service calls after the pipeline completes."""

    def __init__(self, typst_bin: str) -> None:
        self._typst_bin = typst_bin

    def render(
        self,
        document: DraftDocument,
        structured_profile: dict[str, Any],
        jd_text: str = "",
        cover_letter_chunk_ids: frozenset[str] = frozenset(),
    ) -> RenderOutcome:
        header = build_header(structured_profile)

        def render_fn(doc: DraftDocument) -> tuple[bytes, int]:
            return compile_typst(doc, header, self._typst_bin)

        if document.doc_type == "cv":
            return enforce_page_limit(
                document, render_fn, jd_text, cover_letter_chunk_ids
            )
        pdf_bytes, pages = render_fn(document)
        return RenderOutcome(pdf_bytes=pdf_bytes, pages=pages, document=document)
