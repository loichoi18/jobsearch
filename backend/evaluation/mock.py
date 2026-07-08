"""Deterministic mocks for the evaluation harness (Prompt 11).

`--mock` must run in CI for free and produce identical numbers every time, so
we replace the two non-deterministic dependencies of the pipeline:

- MockProvider: returns schema-valid draft/review/verifier JSON derived from
  the case. The "good" configuration never emits forbidden claims (grounding
  100%, fabrication 0%). A `leak_forbidden` configuration deliberately injects
  them so tests can prove the fabrication metric catches leaks.
- InMemoryRetriever: ranks reference-profile chunks by lexical overlap with the
  JD — no embeddings, no database. Also usable in real runs to keep the harness
  self-contained (no per-user DB state required).
"""

from __future__ import annotations

import json
from typing import Any

from generation.doc_schemas import DraftDocument
from generation.provider import LLMProvider
from retrieval.schemas import RetrievedChunk

from evaluation.schemas import EvalCase


# --------------------------------------------------------------- chunks
def profile_to_chunks(profile: dict[str, Any]) -> list[RetrievedChunk]:
    """Turn the reference profile into retrievable chunks (one per item)."""
    chunks: list[RetrievedChunk] = []

    for i, edu in enumerate(profile.get("education", [])):
        text = f"{edu.get('degree','')} at {edu.get('institution','')} " + " ".join(
            edu.get("highlights", [])
        )
        chunks.append(
            RetrievedChunk(id=f"edu-{i}", section="education", content=text, score=0.0)
        )
    for i, exp in enumerate(profile.get("experience", [])):
        text = f"{exp.get('role','')} at {exp.get('company','')}: " + " ".join(
            exp.get("outcomes", [])
        )
        chunks.append(
            RetrievedChunk(id=f"exp-{i}", section="experience", content=text, score=0.0)
        )
    for i, proj in enumerate(profile.get("projects", [])):
        text = (
            f"{proj.get('name','')}: {proj.get('description','')} "
            f"Tech: {', '.join(proj.get('tech', []))}. "
            + " ".join(proj.get("outcomes", []))
        )
        chunks.append(
            RetrievedChunk(id=f"proj-{i}", section="projects", content=text, score=0.0)
        )
    skills = profile.get("skills", {})
    skills_text = "Skills: " + ", ".join(
        skills.get("technical", []) + skills.get("tools", [])
    )
    chunks.append(
        RetrievedChunk(id="skills", section="skills", content=skills_text, score=0.0)
    )
    return chunks


class InMemoryRetriever:
    """Lexical top-k retriever over a fixed chunk set (no DB, no embeddings)."""

    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks

    async def search(
        self, query: str, user_id: str, k: int = 12
    ) -> list[RetrievedChunk]:
        query_terms = {t for t in query.lower().split() if len(t) > 2}
        scored: list[RetrievedChunk] = []
        for c in self._chunks:
            content_terms = set(c.content.lower().split())
            overlap = len(query_terms & content_terms)
            scored.append(c.model_copy(update={"score": float(overlap)}))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]


# ------------------------------------------------------------- provider
class MockProvider(LLMProvider):
    """Deterministic, schema-valid LLM stand-in for one case."""

    def __init__(
        self,
        case: EvalCase,
        chunks: list[RetrievedChunk],
        leak_forbidden: bool = False,
    ) -> None:
        self._case = case
        self._chunk_ids = [c.id for c in chunks] or ["skills"]
        self._leak = leak_forbidden
        self._last_unit_count = 0

    async def complete(
        self,
        system: str,
        user: str,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        title = (json_schema or {}).get("title", "")
        if title == "DraftDocument":
            return self._draft()
        if title == "ReviewResult":
            return self._review()
        if title == "VerifierResult":
            return self._verify()
        return "{}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 768 for _ in texts]

    # ---------------------------------------------------------- stages
    def _draft(self) -> str:
        kws = self._case.expected_keywords
        cid = self._chunk_ids[0]
        cid2 = self._chunk_ids[min(1, len(self._chunk_ids) - 1)]

        def bullet(text: str, chunk_ids: list[str]) -> dict[str, Any]:
            return {"text": text, "chunk_ids": chunk_ids}

        # Weave the expected keywords into grounded, non-generic sentences.
        kw_join = ", ".join(kws[:4]) if kws else "the role's core skills"
        para1 = (
            f"I am applying for the {self._case.title} role. My work centres on "
            f"{kw_join}, which map directly to what you describe."
        )
        para2 = (
            "In my LLM Evaluation Harness project I built grounding-rate and "
            f"fabrication checks in {kws[0] if kws else 'Python'}, with automated "
            "tests in CI."
        )
        para3 = (
            "Through my RAG Job Copilot I implemented hybrid retrieval and a "
            "claim-to-evidence verifier"
        )
        if len(kws) > 4:
            para3 += ", covering " + ", ".join(kws[4:8])
        para3 += "."
        para4 = "I would welcome the chance to discuss how I can contribute."

        if self._leak and self._case.forbidden_claims:
            # Fabrication trap: assert a skill the profile does not support.
            claim = self._case.forbidden_claims[0]
            para3 = f"{para3} I am also highly experienced with {claim}."

        if self._case.doc_type == "cover_letter":
            units = [
                bullet(para1, [cid]),
                bullet(para2, [cid]),
                bullet(para3, [cid2]),
                bullet(para4, []),
            ]
            doc = {
                "doc_type": "cover_letter",
                "sections": [{"title": "letter", "units": units}],
            }
        else:  # cv
            doc = {
                "doc_type": "cv",
                "sections": [
                    {
                        "title": "Summary",
                        "units": [bullet(para1, [cid])],
                    },
                    {
                        "title": "Projects",
                        "units": [bullet(para2, [cid]), bullet(para3, [cid2])],
                    },
                    {
                        "title": "Closing",
                        "units": [bullet(para4, [])],
                    },
                ],
            }

        document = DraftDocument.model_validate(doc)
        self._last_unit_count = len(document.all_units())
        return json.dumps(doc)

    def _review(self) -> str:
        # Clean review → no revision cycle (keeps the mock at 3 calls, fast).
        return json.dumps(
            {
                "scores": {
                    "keyword_coverage": 88,
                    "specificity": 82,
                    "structure": 85,
                    "tone": 84,
                    "red_flags": 95,
                },
                "mandatory_fixes": [],
                "suggestions": [],
            }
        )

    def _verify(self) -> str:
        # Every drafted unit is grounded in the cited profile chunk. The leaked
        # forbidden claim (if any) rides along inside an otherwise-grounded unit,
        # so the fabrication metric — not the verifier — is what must catch it.
        checks = [
            {"index": i, "verdict": "grounded", "note": None}
            for i in range(self._last_unit_count)
        ]
        return json.dumps({"checks": checks})


class RecordingProvider(LLMProvider):
    """Wraps a provider and totals prompt+response characters for cost estimates."""

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.total_chars = 0

    async def complete(
        self,
        system: str,
        user: str,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        response = await self._inner.complete(system, user, json_schema)
        self.total_chars += len(system) + len(user) + len(response)
        return response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.total_chars += sum(len(t) for t in texts)
        return await self._inner.embed(texts)
