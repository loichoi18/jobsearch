"""Generation pipeline (Prompt 6): Drafter → Reviewer → Revision → Verifier.

- All prompts are versioned templates in generation/prompts/*.md — never
  inline strings (CLAUDE.md).
- The reviewer runs with FRESH context: it sees only the JD and the draft,
  never the drafter prompt or the profile.
- Exactly ONE revision cycle (cost control).
- The verifier audits every unit's chunk citations; unsupported units are
  REMOVED from the document and listed in the grounding report.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from generation.doc_schemas import (
    ClaimVerdict,
    DocType,
    DraftDocument,
    GenerationResult,
    GroundingReport,
    ReviewResult,
    VerifierResult,
)
from generation.provider import LLMProvider
from retrieval.hybrid import HybridRetriever
from retrieval.schemas import RetrievedChunk

PROMPTS_DIR = Path(__file__).parent / "prompts"
RETRIEVAL_K = 12
RETRIEVAL_QUERY_CHARS = 1500
MAX_JD_CHARS = 8000


class PipelineError(RuntimeError):
    """A pipeline stage produced invalid output after one retry."""


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def compute_grounding(
    document: DraftDocument, verifier: VerifierResult
) -> tuple[DraftDocument, GroundingReport]:
    """Strip unsupported units; build the report. Pure function (unit-tested).

    Missing indices in the verifier output are treated as unsupported —
    an unaudited claim must never ship.
    """
    units = document.all_units()
    verdict_by_index = {c.index: c for c in verifier.checks}

    claims: list[ClaimVerdict] = []
    removed: list[str] = []
    for i, unit in enumerate(units):
        check = verdict_by_index.get(i)
        verdict = check.verdict if check is not None else "unsupported"
        note = (
            check.note
            if check is not None
            else "Not audited by the verifier — removed defensively."
        )
        claims.append(
            ClaimVerdict(
                claim=unit.text,
                chunk_ids=unit.chunk_ids,
                verdict=verdict,
                note=note,
            )
        )
        if verdict == "unsupported":
            removed.append(unit.text)

    grounded = sum(1 for c in claims if c.verdict == "grounded")
    rate = grounded / len(claims) if claims else 1.0

    removed_set = set(removed)
    cleaned_sections = []
    for section in document.sections:
        kept = [u for u in section.units if u.text not in removed_set]
        if kept:
            cleaned_sections.append(
                section.model_copy(update={"units": kept})
            )
    cleaned = document.model_copy(update={"sections": cleaned_sections})

    report = GroundingReport(
        claims=claims,
        grounding_rate=round(rate, 4),
        removed_claims=removed,
    )
    return cleaned, report


class GenerationPipeline:
    def __init__(
        self, provider: LLMProvider, retriever: HybridRetriever
    ) -> None:
        self._provider = provider
        self._retriever = retriever

    async def generate(
        self,
        user_id: str,
        doc_type: DocType,
        jd_text: str,
        structured_profile: dict,
    ) -> GenerationResult:
        jd_text = jd_text.strip()[:MAX_JD_CHARS]
        chunks = await self._retriever.search(
            jd_text[:RETRIEVAL_QUERY_CHARS], user_id, RETRIEVAL_K
        )

        draft = await self._draft(doc_type, jd_text, structured_profile, chunks)
        review = await self._review(jd_text, draft)
        if review.mandatory_fixes:
            draft = await self._revise(
                doc_type, jd_text, structured_profile, chunks, draft, review
            )
        verifier = await self._verify(draft, chunks)
        document, grounding = compute_grounding(draft, verifier)

        return GenerationResult(
            document=document, review=review, grounding=grounding
        )

    # ------------------------------------------------------------- stages
    async def _draft(
        self,
        doc_type: DocType,
        jd_text: str,
        profile: dict,
        chunks: list[RetrievedChunk],
    ) -> DraftDocument:
        system = load_prompt(f"drafter_{doc_type}")
        user = self._drafter_user_prompt(jd_text, profile, chunks)
        return await self._validated_call(system, user, DraftDocument)

    async def _review(self, jd_text: str, draft: DraftDocument) -> ReviewResult:
        """Fresh context: only the JD and the draft — no profile, no prompts."""
        system = load_prompt("reviewer")
        user = (
            f"JOB DESCRIPTION:\n\"\"\"\n{jd_text}\n\"\"\"\n\n"
            f"DRAFT DOCUMENT ({draft.doc_type}):\n"
            f"\"\"\"\n{self._render_draft_text(draft)}\n\"\"\"\n\n"
            "Review the draft and return the JSON."
        )
        return await self._validated_call(system, user, ReviewResult)

    async def _revise(
        self,
        doc_type: DocType,
        jd_text: str,
        profile: dict,
        chunks: list[RetrievedChunk],
        draft: DraftDocument,
        review: ReviewResult,
    ) -> DraftDocument:
        """ONE revision cycle only (cost control)."""
        system = (
            f"{load_prompt(f'drafter_{doc_type}')}\n\n{load_prompt('revision')}"
        )
        fixes = "\n".join(f"- {f}" for f in review.mandatory_fixes)
        suggestions = "\n".join(f"- {s}" for s in review.suggestions)
        user = (
            f"{self._drafter_user_prompt(jd_text, profile, chunks)}\n\n"
            f"YOUR PREVIOUS DRAFT:\n{draft.model_dump_json()}\n\n"
            f"MANDATORY FIXES:\n{fixes or '- (none)'}\n\n"
            f"SUGGESTIONS:\n{suggestions or '- (none)'}"
        )
        return await self._validated_call(system, user, DraftDocument)

    async def _verify(
        self, draft: DraftDocument, chunks: list[RetrievedChunk]
    ) -> VerifierResult:
        system = load_prompt("verifier")
        chunk_lookup = {c.id: c for c in chunks}
        lines: list[str] = []
        for i, unit in enumerate(draft.all_units()):
            cited = [
                f"  [{cid}] {chunk_lookup[cid].content}"
                for cid in unit.chunk_ids
                if cid in chunk_lookup
            ]
            cited_text = "\n".join(cited) if cited else "  (no chunks cited)"
            lines.append(f"CLAIM {i}: {unit.text}\nCITED CHUNKS:\n{cited_text}")
        user = (
            "Audit the following claims:\n\n"
            + "\n\n".join(lines)
            + "\n\nReturn one check per claim index."
        )
        return await self._validated_call(system, user, VerifierResult)

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _drafter_user_prompt(
        jd_text: str, profile: dict, chunks: list[RetrievedChunk]
    ) -> str:
        chunks_text = "\n".join(
            f"[{c.id}] ({c.section}) {c.content}" for c in chunks
        )
        return (
            f"JOB DESCRIPTION:\n\"\"\"\n{jd_text}\n\"\"\"\n\n"
            f"STRUCTURED PROFILE:\n{json.dumps(profile, ensure_ascii=False)}\n\n"
            f"RETRIEVED EVIDENCE CHUNKS (cite these ids):\n{chunks_text}\n\n"
            "Write the document JSON."
        )

    @staticmethod
    def _render_draft_text(draft: DraftDocument) -> str:
        parts: list[str] = []
        for section in draft.sections:
            parts.append(f"## {section.title}")
            parts.extend(f"- {u.text}" for u in section.units)
        return "\n".join(parts)

    async def _validated_call(
        self, system: str, user: str, model: type[BaseModel]
    ) -> BaseModel:
        """LLM call with JSON-schema output, validated with exactly one retry."""
        schema = model.model_json_schema()
        response = await self._provider.complete(
            system=system, user=user, json_schema=schema
        )
        try:
            return model.model_validate(json.loads(response))
        except (json.JSONDecodeError, ValidationError) as first_error:
            retry_user = (
                f"{user}\n\nYour previous output was invalid:\n{first_error}\n"
                "Return corrected JSON that validates against the schema."
            )
            response = await self._provider.complete(
                system=system, user=retry_user, json_schema=schema
            )
            try:
                return model.model_validate(json.loads(response))
            except (json.JSONDecodeError, ValidationError) as second_error:
                raise PipelineError(
                    f"{model.__name__} stage failed after retry: {second_error}"
                ) from second_error
