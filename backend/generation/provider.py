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
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


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


class ClaudeProvider(LLMProvider):
    """Anthropic Claude for generation, over the plain Messages REST API.

    Kept SDK-free and httpx-based to match GeminiProvider and stay light on
    Render's 512MB free tier. Claude has no embedding endpoint, so embeddings
    are delegated to an injected provider (Gemini) — the RAG pipeline is
    unaffected by which model writes the prose.
    """

    def __init__(
        self,
        api_key: str,
        generation_model: str,
        embedder: LLMProvider,
        max_tokens: int = 8000,
        timeout_s: float = 120.0,
    ) -> None:
        if not api_key:
            raise LLMProviderError(
                "anthropic_api_key is not set — required when llm_provider='claude'."
            )
        self._api_key = api_key
        self._generation_model = generation_model
        self._embedder = embedder
        self._max_tokens = max_tokens
        self._timeout_s = timeout_s

    async def complete(
        self,
        system: str,
        user: str,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        if json_schema is not None:
            # Mirror GeminiProvider: instruct JSON in the system prompt rather
            # than using strict structured outputs, so arbitrary internal
            # schemas (without additionalProperties:false) still work.
            system = (
                f"{system}\n\n"
                "Respond ONLY with a single JSON object conforming to this "
                f"JSON Schema, with no prose or markdown fences:\n"
                f"{json.dumps(json_schema)}"
            )

        body: dict[str, Any] = {
            "model": self._generation_model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        data = await self._post("/messages", body)
        try:
            blocks = data["content"]
            text = "".join(b["text"] for b in blocks if b.get("type") == "text")
        except (KeyError, TypeError) as exc:
            raise LLMProviderError(
                f"Unexpected Anthropic response shape: {data}"
            ) from exc
        if not text:
            raise LLMProviderError(f"Anthropic returned no text: {data}")
        return text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._embedder.embed(texts)

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=ANTHROPIC_BASE_URL, timeout=self._timeout_s
        ) as client:
            response = await client.post(
                path,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json=body,
            )
        if response.status_code != 200:
            raise LLMProviderError(
                f"Anthropic API error {response.status_code}: {response.text[:500]}"
            )
        return response.json()


def _build_gemini() -> GeminiProvider:
    settings = get_settings()
    return GeminiProvider(
        api_key=settings.gemini_api_key,
        generation_model=settings.gemini_generation_model,
        embedding_model=settings.gemini_embedding_model,
    )


@lru_cache
def get_provider() -> LLMProvider:
    """Provider singleton chosen from settings.llm_provider ('gemini'|'claude').

    The Claude provider generates with Claude and embeds with Gemini, since
    Anthropic exposes no embedding endpoint.
    """
    settings = get_settings()
    if settings.llm_provider.lower() == "claude":
        return ClaudeProvider(
            api_key=settings.anthropic_api_key,
            generation_model=settings.claude_generation_model,
            embedder=_build_gemini(),
        )
    return _build_gemini()
