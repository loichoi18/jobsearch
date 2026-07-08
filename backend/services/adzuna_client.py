"""Adzuna AU search client with a 10-minute in-memory cache.

Free tier has low rate limits, so identical queries are cached per-process.
"""

import time
from typing import Any

import httpx

from configs.settings import Settings
from services.jobs_schemas import JobSearchResult

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs/au/search"
CACHE_TTL_SECONDS = 600
DEFAULT_WHAT = "machine learning internship"


class AdzunaError(Exception):
    """Raised when Adzuna is unreachable or returns an error."""


def map_result(raw: dict[str, Any]) -> JobSearchResult:
    """Map one raw Adzuna result to our JobSearchResult shape."""
    return JobSearchResult(
        adzuna_id=str(raw.get("id", "")),
        title=raw.get("title") or "Untitled role",
        company=(raw.get("company") or {}).get("display_name"),
        location=(raw.get("location") or {}).get("display_name"),
        salary_min=raw.get("salary_min"),
        salary_max=raw.get("salary_max"),
        snippet=raw.get("description"),
        redirect_url=raw.get("redirect_url"),
    )


class AdzunaClient:
    def __init__(self, settings: Settings) -> None:
        self._app_id = settings.adzuna_app_id
        self._app_key = settings.adzuna_app_key
        self._cache: dict[tuple[str, str, int], tuple[float, dict[str, Any]]] = {}

    def _cached(self, key: tuple[str, str, int]) -> dict[str, Any] | None:
        hit = self._cache.get(key)
        if hit and (time.monotonic() - hit[0]) < CACHE_TTL_SECONDS:
            return hit[1]
        return None

    async def search(
        self,
        what: str = DEFAULT_WHAT,
        where: str = "",
        page: int = 1,
    ) -> tuple[list[JobSearchResult], int | None]:
        """Search Adzuna AU; returns (results, total_count)."""
        key = (what.lower().strip(), where.lower().strip(), page)
        data = self._cached(key)
        if data is None:
            params: dict[str, Any] = {
                "app_id": self._app_id,
                "app_key": self._app_key,
                "what": what,
                "results_per_page": 20,
                "content-type": "application/json",
            }
            if where:
                params["where"] = where
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(f"{ADZUNA_BASE}/{page}", params=params)
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.HTTPError as exc:
                raise AdzunaError(f"Adzuna request failed: {exc}") from exc
            self._cache[key] = (time.monotonic(), data)

        results = [map_result(r) for r in data.get("results", [])]
        return results, data.get("count")
