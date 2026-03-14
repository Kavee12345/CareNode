"""
Zero-leak RAG vector service.

Every insert and search is ALWAYS scoped to user_id.
RLS policy on the table provides a second enforcement layer.
"""
import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from pgvector.sqlalchemy import Vector

from app.models.document import DocumentChunk
from app.services.embedding_service import embed_query
from app.config import settings


async def store_chunks(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    document_id: uuid.UUID,
    chunks: list[str],
    embeddings: list[list[float]],
    doc_type: str,
    original_filename: str,
) -> list[DocumentChunk]:
    """Bulk insert document chunks with their embeddings."""
    rows = []
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = DocumentChunk(
            user_id=user_id,
            agent_id=agent_id,
            document_id=document_id,
            chunk_index=idx,
            chunk_text=chunk_text,
            embedding=embedding,
            metadata_={
                "doc_type": doc_type,
                "original_filename": original_filename,
                "chunk_index": idx,
            },
        )
        db.add(chunk)
        rows.append(chunk)

    await db.flush()
    return rows


async def similarity_search(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    query: str,
    k: Optional[int] = None,
    fetch_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None,
) -> list[dict]:
    """
    Find the top-k most similar chunks for `query`, strictly filtered by user_id.
    Returns list of {chunk_text, score, metadata, document_id}.
    """
    k = k or settings.rag_top_k
    fetch_k = fetch_k or settings.rag_fetch_k
    threshold = similarity_threshold or settings.rag_similarity_threshold

    query_embedding = embed_query(query)

    # pgvector cosine distance operator: <=>
    # 1 - cosine_distance = cosine_similarity
    result = await db.execute(
        text("""
            SELECT
                id,
                chunk_text,
                metadata,
                document_id,
                1 - (embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks
            WHERE user_id = CAST(:user_id AS uuid)
              AND 1 - (embedding <=> CAST(:embedding AS vector)) > :threshold
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :fetch_k
        """),
        {
            "embedding": str(query_embedding),
            "user_id": str(user_id),
            "threshold": threshold,
            "fetch_k": fetch_k,
        },
    )

    rows = result.fetchall()

    # MMR re-ranking: maximize relevance + diversity
    selected = _mmr_rerank(rows, k=k)
    return selected


def _mmr_rerank(rows: list, k: int) -> list[dict]:
    """
    Maximal Marginal Relevance: greedily select chunks that are
    both relevant (high score) and diverse (dissimilar to already selected).
    Simple text-overlap diversity for efficiency.
    """
    if not rows:
        return []

    candidates = [
        {
            "id": str(row.id),
            "chunk_text": row.chunk_text,
            "metadata": row.metadata,
            "document_id": str(row.document_id),
            "score": float(row.score),
        }
        for row in rows
    ]

    selected = []
    selected_texts: set[str] = set()

    while len(selected) < k and candidates:
        best = None
        best_score = -1

        for c in candidates:
            # Penalize chunks that share many words with already selected
            overlap_penalty = _text_overlap(c["chunk_text"], selected_texts)
            adjusted_score = c["score"] * (1 - 0.3 * overlap_penalty)
            if adjusted_score > best_score:
                best_score = adjusted_score
                best = c

        if best:
            selected.append(best)
            selected_texts.update(best["chunk_text"].lower().split())
            candidates.remove(best)

    return selected


def _text_overlap(text: str, existing_words: set[str]) -> float:
    """Return fraction of words in text that are already in existing_words."""
    if not existing_words:
        return 0.0
    words = set(text.lower().split())
    if not words:
        return 0.0
    overlap = len(words & existing_words)
    return overlap / len(words)


async def delete_document_chunks(
    db: AsyncSession, *, user_id: uuid.UUID, document_id: uuid.UUID
) -> None:
    """Delete all chunks for a document (enforces user_id ownership)."""
    await db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.user_id == user_id,  # zero-leak guard
        )
    )
    await db.flush()


async def delete_all_user_chunks(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Delete all chunks for a user (agent reset)."""
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.user_id == user_id)
    )
    await db.flush()
