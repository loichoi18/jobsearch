"""Singleton Supabase client built from typed settings.

Lazy initialisation: no network connection is made at import time,
which keeps unit tests hermetic.
"""

from supabase import Client, create_client

from configs.settings import get_settings

_client: Client | None = None


def get_supabase() -> Client:
    """Return the process-wide Supabase client (service role)."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client
