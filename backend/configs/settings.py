"""Typed application settings. All secrets come from environment variables
(or a local .env file) via pydantic-settings — never hardcode keys (CLAUDE.md).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Supabase
    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str

    # LLM provider selection. "gemini" (default, free tier) or "claude".
    # The abstraction is fixed by the constitution; only the model string and
    # the vendor are env-swappable. Claude has no embedding endpoint, so the
    # Claude provider still uses Gemini for embeddings (RAG) — set both keys.
    llm_provider: str = "gemini"

    # Gemini (generation + embeddings)
    gemini_api_key: str
    gemini_generation_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"

    # Anthropic / Claude (generation only). Required when llm_provider="claude"
    # and by the CV-enhance endpoint. Defaults to the latest Opus.
    anthropic_api_key: str = ""
    claude_generation_model: str = "claude-opus-4-8"

    # Adzuna (AU job search)
    adzuna_app_id: str
    adzuna_app_key: str

    # PDF rendering (Prompt 7): path to the typst binary.
    # Local: install typst and leave as "typst". Render: ./bin/typst
    typst_bin: str = "typst"
    signed_url_ttl_s: int = 300

    # CORS / frontend
    frontend_url: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    """Singleton settings, cached for the process lifetime."""
    return Settings()  # type: ignore[call-arg]  # populated from env
