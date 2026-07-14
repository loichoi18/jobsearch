"""CV-enhance orchestration.

A single grounded LLM call that rewrites a pasted resume against a pasted job
description using the "recruiter / XYZ formula / ATS" prompt. Routers hold no
business logic (CLAUDE.md) — the prompt and the provider call live here.
"""

from generation.provider import LLMProvider, LLMProviderError

# The rewrite rules, kept verbatim so the behaviour is auditable and stable.
_RULES = """Rebuild my resume to match this JD with 90%+ ATS score.
Rules:
1. Mirror exact keywords from the JD
2. Rewrite bullets using XYZ formula (Accomplished X, measured by Y, by doing Z)
3. Quantify every achievement with numbers
4. Cut fluff - only keep what maps to the JD
5. Flag 3 weak spots where I'll get rejected.
Give me the rewritten resume + rejection risks."""


class EnhanceCvError(RuntimeError):
    """The enhance call failed (upstream LLM error)."""


class EnhanceCvService:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def enhance(
        self, company_name: str, resume: str, job_description: str
    ) -> str:
        system = (
            f"You are a {company_name.strip()} recruiter and an expert resume "
            "writer who optimises resumes for Applicant Tracking Systems (ATS). "
            "Only use facts present in the candidate's resume — never invent "
            "employers, titles, dates, or metrics. When a bullet lacks a number, "
            "keep it truthful and mark it as needing a metric rather than "
            "fabricating one."
        )
        user = (
            "I'm pasting my resume and the job JD below.\n\n"
            f"{_RULES}\n\n"
            "=== MY RESUME ===\n"
            f"{resume.strip()}\n\n"
            "=== JOB DESCRIPTION ===\n"
            f"{job_description.strip()}"
        )
        try:
            return await self._provider.complete(system=system, user=user)
        except LLMProviderError as exc:
            raise EnhanceCvError(str(exc)) from exc
