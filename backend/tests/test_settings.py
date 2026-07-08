"""Settings must load fully-typed from environment variables."""

from configs.settings import Settings, get_settings


def test_settings_load_from_env(test_env: dict[str, str]) -> None:
    settings = Settings()

    assert settings.supabase_url == test_env["SUPABASE_URL"]
    assert settings.supabase_service_key == test_env["SUPABASE_SERVICE_KEY"]
    assert settings.gemini_api_key == test_env["GEMINI_API_KEY"]
    assert settings.adzuna_app_id == test_env["ADZUNA_APP_ID"]
    assert settings.adzuna_app_key == test_env["ADZUNA_APP_KEY"]
    assert settings.frontend_url == test_env["FRONTEND_URL"]


def test_model_ids_have_defaults() -> None:
    settings = Settings()
    assert settings.gemini_generation_model  # non-empty default
    assert settings.gemini_embedding_model


def test_get_settings_is_cached_singleton() -> None:
    assert get_settings() is get_settings()
