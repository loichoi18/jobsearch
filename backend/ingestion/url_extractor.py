"""Polite job-description extraction from a public URL.

One request, honest User-Agent, no retries, never bypass blocks (CLAUDE.md:
NEVER scrape Seek or LinkedIn — those domains are refused up front).
"""

from urllib.parse import urlparse

import httpx
from lxml import html as lxml_html
from readability import Document

PASTE_INSTEAD_MESSAGE = (
    "We couldn't fetch that page (the site may block automated access). "
    "Please copy the job description text and paste it instead."
)

# Domains we never fetch — ToS-protected job boards.
BLOCKED_DOMAINS: tuple[str, ...] = ("seek.com.au", "linkedin.com")

_HEADERS = {
    "User-Agent": "JobPilotAU/0.1 (personal job-application assistant)",
    "Accept": "text/html,application/xhtml+xml",
}


class UrlExtractionError(Exception):
    """Fetch failed or was blocked; message tells the user to paste the JD."""

    def __init__(self, message: str = PASTE_INSTEAD_MESSAGE) -> None:
        super().__init__(message)


def is_blocked_domain(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith(f".{d}") for d in BLOCKED_DOMAINS)


def _main_text(page_html: str) -> str:
    """Readability main-content extraction, flattened to plain text."""
    summary_html = Document(page_html).summary(html_partial=True)
    tree = lxml_html.fromstring(summary_html)
    text = "\n".join(
        line.strip()
        for line in tree.text_content().splitlines()
        if line.strip()
    )
    return text


async def extract_jd_from_url(url: str) -> str:
    """Fetch a job posting URL once and return the main text.

    Raises UrlExtractionError with paste-instead guidance for blocked
    domains, HTTP errors, or pages with no extractable content.
    """
    if is_blocked_domain(url):
        raise UrlExtractionError(
            "That site doesn't allow automated access. "
            "Please paste the job description text instead."
        )
    try:
        async with httpx.AsyncClient(
            timeout=10, headers=_HEADERS, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise UrlExtractionError() from exc

    text = _main_text(resp.text)
    if len(text) < 100:
        raise UrlExtractionError()
    return text
