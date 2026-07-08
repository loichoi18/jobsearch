"""PDF text extraction for uploaded CVs."""

from io import BytesIO

from pypdf import PdfReader


class PdfParseError(ValueError):
    """Raised when no usable text can be extracted from the PDF."""


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF, page by page.

    Multi-column layouts are handled gracefully: pypdf returns reading-order
    text where possible; otherwise we fall back to the page text as-is.
    """
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:  # pypdf raises a zoo of exception types
        raise PdfParseError(f"Could not read PDF: {exc}") from exc

    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 — fall back to empty for a bad page
            pages.append("")

    text = "\n\n".join(pages).strip()
    if not text:
        raise PdfParseError(
            "No text could be extracted from this PDF. "
            "If it is a scanned image, please paste the text instead."
        )
    return text
