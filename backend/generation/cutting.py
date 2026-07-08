"""Relevance-weighted CV cutting (CLAUDE.md):

score(bullet) = relevance-to-JD x uniqueness x cover-letter-dependency

When the rendered CV exceeds the page limit, the lowest-scoring bullet is
removed and the CV re-rendered, repeating until it fits (or max iterations).

Factor definitions (documented design choices):
- relevance: token overlap between the bullet and the JD (floor 0.1 so no
  factor can zero the product on its own).
- uniqueness: 1 - max token overlap with any OTHER bullet (floor 0.1) —
  near-duplicate bullets get cut first.
- cover-letter dependency: 1.3 when the bullet cites a profile chunk the
  cover letter also cites, else 1.0. Rationale: the cover letter makes a
  promise; the CV should keep the evidence that backs it up.
"""

import re

from generation.doc_schemas import DraftDocument, DraftUnit

RELEVANCE_FLOOR = 0.1
UNIQUENESS_FLOOR = 0.1
COVER_LETTER_KEEP_BOOST = 1.3

_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it of on or the to with"
    " we you your our their this that will".split()
)
_WORD_RE = re.compile(r"[a-z0-9+#.]+")


def tokenize(text: str) -> frozenset[str]:
    return frozenset(
        w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS
    )


def _overlap(a: frozenset[str], b: frozenset[str]) -> float:
    """Fraction of a's tokens found in b (containment, not Jaccard —
    bullet length shouldn't penalise relevance)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def bullet_score(
    unit: DraftUnit,
    jd_tokens: frozenset[str],
    other_units: list[DraftUnit],
    cover_letter_chunk_ids: frozenset[str],
) -> float:
    tokens = tokenize(unit.text)

    relevance = max(_overlap(tokens, jd_tokens), RELEVANCE_FLOOR)

    max_sim = max(
        (_overlap(tokens, tokenize(o.text)) for o in other_units),
        default=0.0,
    )
    uniqueness = max(1.0 - max_sim, UNIQUENESS_FLOOR)

    dependency = (
        COVER_LETTER_KEEP_BOOST
        if cover_letter_chunk_ids and set(unit.chunk_ids) & cover_letter_chunk_ids
        else 1.0
    )
    return relevance * uniqueness * dependency


def cut_lowest_bullet(
    document: DraftDocument,
    jd_text: str,
    cover_letter_chunk_ids: frozenset[str] = frozenset(),
) -> tuple[DraftDocument, str | None]:
    """Remove the single lowest-scoring bullet. Returns (document, cut_text).

    Sections emptied by the cut are dropped. Returns cut_text=None when
    there is nothing left to cut.
    """
    jd_tokens = tokenize(jd_text)
    all_units = document.all_units()
    if len(all_units) <= 1:
        return document, None

    scored: list[tuple[float, int]] = []
    for i, unit in enumerate(all_units):
        others = all_units[:i] + all_units[i + 1 :]
        scored.append(
            (bullet_score(unit, jd_tokens, others, cover_letter_chunk_ids), i)
        )
    _, cut_index = min(scored, key=lambda pair: pair[0])
    cut_text = all_units[cut_index].text

    new_sections = []
    seen = 0
    for section in document.sections:
        kept_units = []
        for unit in section.units:
            if seen != cut_index:
                kept_units.append(unit)
            seen += 1
        if kept_units:
            new_sections.append(section.model_copy(update={"units": kept_units}))
    return document.model_copy(update={"sections": new_sections}), cut_text
