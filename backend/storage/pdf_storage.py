"""Supabase Storage access for rendered PDFs (private `documents` bucket)."""

from typing import Any, Protocol

from supabase import Client

BUCKET = "documents"


class PdfStorageProtocol(Protocol):
    def upload(self, path: str, pdf_bytes: bytes) -> str: ...

    def signed_url(self, path: str, expires_s: int = 300) -> str: ...


class PdfStorage:
    def __init__(self, client: Client) -> None:
        self._client = client

    def upload(self, path: str, pdf_bytes: bytes) -> str:
        """Upload (upsert) the PDF; returns the storage path."""
        self._client.storage.from_(BUCKET).upload(
            path=path,
            file=pdf_bytes,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true",
            },
        )
        return path

    def signed_url(self, path: str, expires_s: int = 300) -> str:
        result: Any = self._client.storage.from_(BUCKET).create_signed_url(
            path, expires_s
        )
        # supabase-py has renamed this key across versions
        url = result.get("signedURL") or result.get("signedUrl")
        if not url:
            raise RuntimeError(f"No signed URL in storage response: {result}")
        return str(url)
