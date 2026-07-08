"""Hybrid retrieval over an in-memory chunk store: index a profile, then a
query like "hallucination detection" must surface the eval-project chunk."""

import json
import math
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.retrieval import get_retriever
from generation.provider import LLMProvider
from ingestion.profile_schema import Profile
from main import create_app
from retrieval.dense import DenseSearcher
from retrieval.hybrid import HybridRetriever
from retrieval.sparse import SparseSearcher
from services.indexing_service import ProfileIndexer
from tests.test_profile_api import auth_header

FIXTURE = Path(__file__).parent / "fixtures" / "profile_extraction.json"


def _keyword_vector(text: str) -> list[float]:
    """Deterministic toy embedding: presence of vocabulary words -> dims."""
    vocab = [
        "eval", "harness", "llm", "regression", "pytest", "mlflow",
        "python", "pytorch", "sql", "fastapi", "docker",
        "bachelor", "artificial", "intelligence", "uts", "gpa",
        "visa", "citizen", "github", "hallucination", "detection",
    ]
    lower = text.lower()
    vec = [1.0 if word in lower else 0.0 for word in vocab]
    # "hallucination detection" is semantically close to eval/LLM work:
    if "hallucination" in lower or "detection" in lower:
        vec[0] = vec[2] = vec[3] = 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class KeywordEmbedProvider(LLMProvider):
    async def complete(self, system: str, user: str, json_schema=None) -> str:
        raise NotImplementedError

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_keyword_vector(t) for t in texts]


class InMemoryChunkStore:
    """Implements ChunkRepositoryProtocol against a plain list."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.replace_calls = 0

    def replace_chunks(self, user_id: str, rows: list[dict[str, Any]]) -> int:
        self.replace_calls += 1
        self.rows = [r for r in self.rows if r["user_id"] != user_id]
        for i, row in enumerate(rows):
            self.rows.append({**row, "id": f"{user_id}-chunk-{i}"})
        return len(rows)

    def dense_search(
        self, query_embedding: list[float], user_id: str, count: int
    ) -> list[dict[str, Any]]:
        def cosine(a: list[float], b: list[float]) -> float:
            n = min(len(a), len(b))
            return sum(x * y for x, y in zip(a[:n], b[:n]))

        scored = [
            {**r, "similarity": cosine(query_embedding, r["embedding"])}
            for r in self.rows
            if r["user_id"] == user_id
        ]
        scored.sort(key=lambda r: r["similarity"], reverse=True)
        return scored[:count]

    def sparse_search(
        self, query_text: str, user_id: str, count: int
    ) -> list[dict[str, Any]]:
        words = set(query_text.lower().split())
        scored = []
        for r in self.rows:
            if r["user_id"] != user_id:
                continue
            overlap = len(words & set(r["content"].lower().split()))
            if overlap:
                scored.append({**r, "rank": float(overlap)})
        scored.sort(key=lambda r: r["rank"], reverse=True)
        return scored[:count]


@pytest.fixture()
def store() -> InMemoryChunkStore:
    return InMemoryChunkStore()


@pytest.fixture()
def retriever(store: InMemoryChunkStore) -> HybridRetriever:
    return HybridRetriever(
        provider=KeywordEmbedProvider(),
        dense=DenseSearcher(store),
        sparse=SparseSearcher(store),
    )


async def _index_fixture_profile(store: InMemoryChunkStore, user_id: str) -> None:
    profile = Profile.model_validate(json.loads(FIXTURE.read_text("utf-8")))
    indexer = ProfileIndexer(chunk_repo=store, provider=KeywordEmbedProvider())
    await indexer.reindex(user_id, profile)


@pytest.mark.asyncio
async def test_index_then_query_returns_relevant_chunk(
    store: InMemoryChunkStore, retriever: HybridRetriever
) -> None:
    await _index_fixture_profile(store, "user-1")

    results = await retriever.search("hallucination detection eval", "user-1", k=3)

    assert results, "expected results"
    assert "Model Regression Detection" in results[0].content
    assert results[0].section == "project"


@pytest.mark.asyncio
async def test_reindex_is_idempotent(store: InMemoryChunkStore) -> None:
    await _index_fixture_profile(store, "user-1")
    first_count = len(store.rows)
    await _index_fixture_profile(store, "user-1")

    assert len(store.rows) == first_count  # replaced, not appended
    assert store.replace_calls == 2


@pytest.mark.asyncio
async def test_results_are_user_scoped(
    store: InMemoryChunkStore, retriever: HybridRetriever
) -> None:
    await _index_fixture_profile(store, "user-1")
    results = await retriever.search("eval harness", "someone-else", k=5)
    assert results == []


def test_retrieval_endpoint(store: InMemoryChunkStore) -> None:
    import asyncio

    asyncio.run(
        _index_fixture_profile(store, "11111111-2222-3333-4444-555555555555")
    )
    app = create_app()
    app.dependency_overrides[get_retriever] = lambda: HybridRetriever(
        provider=KeywordEmbedProvider(),
        dense=DenseSearcher(store),
        sparse=SparseSearcher(store),
    )
    client = TestClient(app)

    response = client.post(
        "/api/retrieval/query",
        json={"query": "LLM evaluation", "k": 3},
        headers=auth_header(),
    )
    assert response.status_code == 200, response.text
    chunks = response.json()["chunks"]
    assert chunks
    assert any("Regression Detection" in c["content"] for c in chunks)

    # And unauthenticated is rejected
    assert (
        client.post(
            "/api/retrieval/query", json={"query": "LLM evaluation"}
        ).status_code
        == 401
    )
