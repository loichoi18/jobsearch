"""Match scoring: semantic similarity + LLM rubric, combined 0.3/0.7.

match_score = 0.3 * semantic_score * 100 + 0.7 * rubric_score
- semantic_score: cosine similarity between the JD embedding and the MEAN of
  the user's profile-chunk embeddings, clamped to [0, 1].
- rubric_score: LLM evaluation against top-8 hybrid-retrieved profile chunks,
  JSON-schema constrained, Pydantic-validated with exactly one retry.
"""

import json
import logging
import math
from typing import Protocol

from pydantic import ValidationError

from generation.provider import LLMProvider
from retrieval.hybrid import HybridRetriever
from services.matching_schemas import MatchAnalysis, RubricResult
from services.jobs_service import JobNotFoundError
from storage.repositories import JobRepositoryProtocol

logger = logging.getLogger(__name__)

# ~2000 tokens at ~4 chars/token.
MAX_JD_CHARS = 8000
# Below this the JD is probably a truncated snippet, not a full posting.
SHORT_DESCRIPTION_CHARS = 400
SEMANTIC_WEIGHT = 0.3
RUBRIC_WEIGHT = 0.7
RETRIEVAL_K = 8
# Sparse FTS queries choke on multi-page text; retrieve with a JD prefix.
RETRIEVAL_QUERY_CHARS = 1500


class MatchAnalysisError(RuntimeError):
    """LLM rubric output was invalid after one retry (surfaces as 502)."""


class EmbeddingListRepo(Protocol):
    """The one storage capability matching needs beyond retrieval."""

    def list_embeddings(self, user_id: str) -> list[list[float]]: ...


class NoProfileError(RuntimeError):
    """User has no indexed profile chunks yet."""


RUBRIC_SYSTEM_PROMPT = """You are a rigorous graduate-recruitment screener \
for the Australian market.
Score how well the candidate's profile evidence matches the job description.

Hard rules:
- Judge ONLY from the provided profile chunks. Do not assume unlisted skills.
- matched_skills: skills the JD wants that ARE evidenced in the chunks.
- missing_skills: skills the JD wants with NO evidence in the chunks. For
  each, set importance to "required" if the JD demands it (must have,
  essential, required) or "preferred" (nice to have, desirable, bonus), and
  quote the exact JD phrase as evidence.
- Scores are 0-100 integers. rubric_score is your overall judgement, not a
  mechanical average of the breakdown.
- one_line_verdict: a single frank sentence a career adviser would say.
"""


def _rubric_user_prompt(jd_text: str, chunks_text: str) -> str:
    return (
        f"JOB DESCRIPTION:\n\"\"\"\n{jd_text}\n\"\"\"\n\n"
        f"CANDIDATE PROFILE EVIDENCE (retrieved chunks):\n"
        f"\"\"\"\n{chunks_text}\n\"\"\"\n\n"
        "Evaluate the match and return the JSON."
    )


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def mean_vector(vectors: list[list[float]]) -> list[float]:
    n = len(vectors)
    return [sum(col) / n for col in zip(*vectors)]


def combine_scores(semantic_score: float, rubric_score: int) -> float:
    """match_score = 0.3 * semantic * 100 + 0.7 * rubric, rounded to 1dp."""
    return round(
        SEMANTIC_WEIGHT * semantic_score * 100 + RUBRIC_WEIGHT * rubric_score, 1
    )


class MatchingService:
    def __init__(
        self,
        provider: LLMProvider,
        retriever: HybridRetriever,
        chunk_repo: EmbeddingListRepo,
        job_repo: JobRepositoryProtocol,
    ) -> None:
        self._provider = provider
        self._retriever = retriever
        self._chunk_repo = chunk_repo
        self._job_repo = job_repo

    async def analyze(self, user_id: str, job_id: str) -> MatchAnalysis:
        """Score one saved job against the profile; persist the result."""
        job = self._job_repo.get(user_id, job_id)
        if job is None:
            raise JobNotFoundError(job_id)

        jd_text = (job.get("description") or "").strip()[:MAX_JD_CHARS]
        if not jd_text:
            jd_text = job.get("title") or ""

        semantic_score = await self._semantic_score(user_id, jd_text)
        rubric = await self._rubric_score(user_id, jd_text)

        analysis = MatchAnalysis(
            match_score=combine_scores(semantic_score, rubric.rubric_score),
            semantic_score=round(max(0.0, min(1.0, semantic_score)), 4),
            rubric_score=rubric.rubric_score,
            breakdown=rubric.breakdown,
            matched_skills=rubric.matched_skills,
            missing_skills=rubric.missing_skills,
            one_line_verdict=rubric.one_line_verdict,
            short_description=len(jd_text) < SHORT_DESCRIPTION_CHARS,
        )

        self._job_repo.update(
            user_id,
            job_id,
            {
                "match_score": analysis.match_score,
                "skill_gaps": analysis.model_dump(),
            },
        )
        return analysis

    async def analyze_quietly(self, user_id: str, job_id: str) -> None:
        """Best-effort background analysis (used on job save)."""
        try:
            await self.analyze(user_id, job_id)
        except Exception:  # noqa: BLE001 — background task must never raise
            logger.exception("Background match analysis failed for %s", job_id)

    async def _semantic_score(self, user_id: str, jd_text: str) -> float:
        embeddings = self._chunk_repo.list_embeddings(user_id)
        if not embeddings:
            raise NoProfileError(
                "No indexed profile yet — upload your CV first."
            )
        jd_embedding = (await self._provider.embed([jd_text]))[0]
        similarity = cosine_similarity(jd_embedding, mean_vector(embeddings))
        return max(0.0, min(1.0, similarity))

    async def _rubric_score(self, user_id: str, jd_text: str) -> RubricResult:
        chunks = await self._retriever.search(
            jd_text[:RETRIEVAL_QUERY_CHARS], user_id, RETRIEVAL_K
        )
        chunks_text = "\n\n".join(
            f"[{c.section}] {c.content}" for c in chunks
        ) or "(no profile chunks retrieved)"

        schema = RubricResult.model_json_schema()
        user_prompt = _rubric_user_prompt(jd_text, chunks_text)
        response = await self._provider.complete(
            system=RUBRIC_SYSTEM_PROMPT, user=user_prompt, json_schema=schema
        )
        try:
            return RubricResult.model_validate(json.loads(response))
        except (json.JSONDecodeError, ValidationError) as first_error:
            retry_prompt = (
                f"{user_prompt}\n\nYour previous output was invalid:\n"
                f"{first_error}\nReturn corrected JSON that validates."
            )
            response = await self._provider.complete(
                system=RUBRIC_SYSTEM_PROMPT,
                user=retry_prompt,
                json_schema=schema,
            )
            try:
                return RubricResult.model_validate(json.loads(response))
            except (json.JSONDecodeError, ValidationError) as second_error:
                raise MatchAnalysisError(
                    f"Rubric evaluation failed after retry: {second_error}"
                ) from second_error
