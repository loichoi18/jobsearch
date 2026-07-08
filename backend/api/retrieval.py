"""Retrieval debug/demo endpoint. Internal callers use HybridRetriever directly."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.deps import CurrentUserId
from generation.provider import get_provider
from retrieval.dense import DenseSearcher
from retrieval.hybrid import HybridRetriever
from retrieval.schemas import RetrievedChunk
from retrieval.sparse import SparseSearcher
from storage.repositories import ChunkRepository
from storage.supabase_client import get_supabase

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


def get_retriever() -> HybridRetriever:
    repo = ChunkRepository(get_supabase())
    return HybridRetriever(
        provider=get_provider(),
        dense=DenseSearcher(repo),
        sparse=SparseSearcher(repo),
    )


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=2)
    k: int = Field(default=8, ge=1, le=50)


class RetrievalResponse(BaseModel):
    chunks: list[RetrievedChunk]


@router.post("/query", response_model=RetrievalResponse)
async def query_profile_chunks(
    body: RetrievalQuery,
    user_id: CurrentUserId,
    retriever: HybridRetriever = Depends(get_retriever),
) -> RetrievalResponse:
    chunks = await retriever.search(body.query, user_id, body.k)
    return RetrievalResponse(chunks=chunks)
