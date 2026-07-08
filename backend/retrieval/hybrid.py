"""Hybrid retrieval: dense + sparse fused with Reciprocal Rank Fusion.

RRF (k=60): score(d) = sum over rankings of 1 / (k + rank_of_d).
Rank-based fusion sidesteps the incomparable-score-scales problem between
cosine similarity and ts_rank.
"""

from generation.provider import LLMProvider
from retrieval.dense import DenseSearcher
from retrieval.schemas import RetrievedChunk
from retrieval.sparse import SparseSearcher

RRF_K = 60


def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = RRF_K
) -> dict[str, float]:
    """Fuse ranked id lists into {id: rrf_score}. Ranks are 1-based."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


class HybridRetriever:
    def __init__(
        self,
        provider: LLMProvider,
        dense: DenseSearcher,
        sparse: SparseSearcher,
    ) -> None:
        self._provider = provider
        self._dense = dense
        self._sparse = sparse

    async def search(
        self, query: str, user_id: str, k: int = 8
    ) -> list[RetrievedChunk]:
        fetch_count = max(k * 2, 16)

        query_embedding = (await self._provider.embed([query]))[0]
        dense_results = self._dense.search(query_embedding, user_id, fetch_count)
        sparse_results = self._sparse.search(query, user_id, fetch_count)

        fused = reciprocal_rank_fusion(
            [
                [c.id for c in dense_results],
                [c.id for c in sparse_results],
            ]
        )

        by_id: dict[str, RetrievedChunk] = {}
        for chunk in [*dense_results, *sparse_results]:
            by_id.setdefault(chunk.id, chunk)

        top = sorted(fused.items(), key=lambda item: item[1], reverse=True)[:k]
        return [
            by_id[chunk_id].model_copy(update={"score": score})
            for chunk_id, score in top
        ]
