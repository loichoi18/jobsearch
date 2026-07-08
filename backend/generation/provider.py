"""LLM provider abstraction (CLAUDE.md: business logic NEVER calls a vendor
SDK directly — everything goes through LLMProvider so the vendor can be
swapped via config).

The Gemini implementation uses the plain REST API over httpx: no SDK
dependency, trivially mockable, and light on Render's 512MB free tier.
"""

import json
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

import httpx

from configs.settings import get_settings

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class LLMProviderError(RuntimeError):
    """Raised when the underlying LLM API fails."""


class LLMProvider(ABC):
    """Vendor-agnostic LLM interface used by drafter/reviewer/verifier/extractor."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        """Return the model's text response. If json_schema is given, the
        response is requested as JSON conforming to that schema."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        generation_model: str,
        embedding_model: str,
        timeout_s: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._generation_model = generation_model
        self._embedding_model = embedding_model
        self._timeout_s = timeout_s

    async def complete(
        self,
        system: str,
        user: str,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        generation_config: dict[str, Any] = {"temperature": 0.2}
        if json_schema is not None:
            generation_config["responseMimeType"] = "application/json"
            system = (
                f"{system}\n\n"
                "Respond ONLY with a single JSON object conforming to this "
                f"JSON Schema:\n{json.dumps(json_schema)}"
            )

        body = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": generation_config,
        }
        data = await self._post(
            f"/models/{self._generation_model}:generateContent", body
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"Unexpected Gemini response shape: {data}") from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        body = {
            "requests": [
                {
                    "model": f"models/{self._embedding_model}",
                    "content": {"parts": [{"text": text}]},
                }
                for text in texts
            ]
        }
        data = await self._post(
            f"/models/{self._embedding_model}:batchEmbedContents", body
        )
        try:
            return [item["values"] for item in data["embeddings"]]
        except KeyError as exc:
            raise LLMProviderError(f"Unexpected Gemini response shape: {data}") from exc

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=GEMINI_BASE_URL, timeout=self._timeout_s
        ) as client:
            response = await client.post(
                path, params={"key": self._api_key}, json=body
            )
        if response.status_code != 200:
            raise LLMProviderError(
                f"Gemini API error {response.status_code}: {response.text[:500]}"
            )
        return response.json()


@lru_cache
def get_provider() -> LLMProvider:
    """Provider singleton chosen from settings (swap point for Claude later)."""
    settings = get_settings()
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        generation_model=settings.gemini_generation_model,
        embedding_model=settings.gemini_embedding_model,
    )
