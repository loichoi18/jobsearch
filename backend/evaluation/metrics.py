"""Evaluation metrics (Prompt 11) — all pure functions, unit-tested.

Kept free of pipeline/IO concerns so the harness can compose them and the
tests can assert the maths directly, including the fabrication-trap logic.

Term matching is word-boundary aware on purpose: a naive substring check would
count the forbidden claim "Go" inside "good" or "category" and wreck the
fabrication metric. We match a term only when it is not flanked by another
alphanumeric character.
"""

from __future__ import annotations

import re

from generation.doc_schemas import DraftDocument

# Rough char-per-token ratio for cost estimation (Gemini/most BPE tokenizers).
CHARS_PER_TOKEN = 4
# Words that fill roughly one page of a single-column A4 CV/letter.
WORDS_PER_PAGE = 500


def contains_term(text: str, term: str) -> bool:
    """True if `term` occurs in `text` as a whole token (case-insensitive)."""
    term = term.strip().lower()
    if not term:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
    return re.search(pattern, text.lower()) is not None


def document_text(document: DraftDocument) -> str:
    """Flatten a document's final unit texts into one searchable string."""
    return "\n".join(u.text for u in document.all_units())


def keyword_coverage(
    expected: list[str], text: str
) -> tuple[float, list[str]]:
    """Fraction of expected keywords present; also the ones missing."""
    if not expected:
        return 1.0, []
    missing = [kw for kw in expected if not contains_term(text, kw)]
    covered = len(expected) - len(missing)
    return covered / len(expected), missing


def fabrication_rate(
    forbidden: list[str], text: str
) -> tuple[float, list[str]]:
    """Fraction of forbidden claims that leaked into the output; the leaks.

    The fabrication trap: forbidden claims are skills the JD demands but the
    reference profile lacks. A correctly grounded pipeline must never surface
    them — target rate is 0.
    """
    if not forbidden:
        return 0.0, []
    leaked = [claim for claim in forbidden if contains_term(text, claim)]
    return len(leaked) / len(forbidden), leaked


def estimate_pages(document: DraftDocument) -> int:
    """Heuristic page count from word volume (used when Typst is unavailable)."""
    words = sum(len(u.text.split()) for u in document.all_units())
    return max(1, -(-words // WORDS_PER_PAGE))  # ceil division, min 1 page


def length_compliant(pages: int | None, max_pages: int) -> bool:
    """A missing page count is treated as compliant only when unavoidable."""
    if pages is None:
        return True
    return pages <= max_pages


def estimate_tokens(char_count: int) -> int:
    return char_count // CHARS_PER_TOKEN


def estimate_cost_usd(tokens: int, usd_per_1k_tokens: float) -> float:
    """Cost estimate. Gemini free tier is $0; a non-zero rate models the
    swap-to-Claude story (the harness passes the configured rate)."""
    return round(tokens / 1000 * usd_per_1k_tokens, 6)
