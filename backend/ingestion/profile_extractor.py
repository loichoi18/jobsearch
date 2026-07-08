"""CV text -> structured Profile via the LLM provider.

Hard rule (CLAUDE.md): the extractor must NOT invent data. Anything absent
from the source text is null/empty. Output is validated against the Profile
schema with exactly one retry on validation failure.
"""

import json

from pydantic import ValidationError

from generation.provider import LLMProvider
from ingestion.profile_schema import Profile


class ProfileExtractionError(RuntimeError):
    """Raised when the LLM output cannot be validated after one retry."""


SYSTEM_PROMPT = """You are a precise CV/resume parser.
Convert the raw CV text into the structured JSON profile schema provided.

Hard rules:
- Use ONLY information explicitly present in the text. NEVER invent, infer,
  or embellish skills, dates, grades, employers, or achievements.
- If a field is not present in the text, output null (or an empty list/object).
- Keep bullet points verbatim or near-verbatim; do not rewrite achievements.
- Dates: keep the format found in the text (e.g. "Mar 2024", "2023-2025").
- links: map of label -> URL for any URLs found (github, linkedin, portfolio).
"""


def _user_prompt(raw_text: str) -> str:
    return f"Raw CV text:\n\"\"\"\n{raw_text}\n\"\"\"\n\nExtract the profile JSON."


async def extract_profile(raw_text: str, provider: LLMProvider) -> Profile:
    schema = Profile.model_json_schema()
    response = await provider.complete(
        system=SYSTEM_PROMPT, user=_user_prompt(raw_text), json_schema=schema
    )

    try:
        return Profile.model_validate(json.loads(response))
    except (json.JSONDecodeError, ValidationError) as first_error:
        retry_user = (
            f"{_user_prompt(raw_text)}\n\n"
            f"Your previous output was invalid:\n{first_error}\n"
            "Return corrected JSON that validates against the schema."
        )
        response = await provider.complete(
            system=SYSTEM_PROMPT, user=retry_user, json_schema=schema
        )
        try:
            return Profile.model_validate(json.loads(response))
        except (json.JSONDecodeError, ValidationError) as second_error:
            raise ProfileExtractionError(
                f"Profile extraction failed after retry: {second_error}"
            ) from second_error
