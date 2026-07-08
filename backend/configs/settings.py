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

    # LLM provider (Gemini free tier; model IDs are env-swappable so the
    # constitution fixes the abstraction, not the model string)
    gemini_api_key: str
    gemini_generation_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"

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
