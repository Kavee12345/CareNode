"""
Background task: OCR → Chunk → Embed → Store in pgvector.
Runs as a FastAPI BackgroundTask (in-process, async).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.common_types import DocumentType
from app.models.document import Document
from app.services.chunking_service import chunk_text
from app.services.embedding_service import embed_texts
from app.services.ocr_service import detect_doc_type, extract_text
from app.services.vector_service import store_chunks


async def process_document(
    document_type: DocumentType,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> None:
    """
    Full OCR → chunk → embed pipeline for a single document.
    Called as a FastAPI BackgroundTask after upload.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Fetch document record
            result = await db.execute(
                select(Document).where(
                    Document.id == document_id,
                    Document.user_id == user_id,  # zero-leak guard
                )
            )
            doc = result.scalar_one_or_none()
            if not doc:
                return

            # Mark as processing
            doc.processing_status = "processing"
            await db.commit()

            # Download raw file from MinIO
            from app.services.storage_service import download_file

            file_bytes = download_file(doc.minio_key)

            # Step 1: Extract text
            text, page_count = extract_text(file_bytes, doc.mime_type, document_type)
            doc.extracted_text = text
            doc.page_count = page_count

            # Step 2: Detect doc type if not already set
            if not doc.doc_type:
                doc.doc_type = detect_doc_type(doc.original_name, text[:500])

            # Step 3: Chunk text
            chunks = chunk_text(text, doc.doc_type or "other")
            if not chunks:
                doc.processing_status = "done"
                await db.commit()
                return

            # Step 4: Embed chunks
            embeddings = embed_texts(chunks)

            # Step 5: Store in pgvector
            await store_chunks(
                db,
                user_id=user_id,
                agent_id=agent_id,
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings,
                doc_type=doc.doc_type or "other",
                original_filename=doc.original_name,
            )

            doc.processing_status = "done"
            await db.commit()

        except Exception as e:
            async with AsyncSessionLocal() as err_db:
                err_result = await err_db.execute(
                    select(Document).where(Document.id == document_id)
                )
                err_doc = err_result.scalar_one_or_none()
                if err_doc:
                    err_doc.processing_status = "failed"
                    err_doc.processing_error = str(e)
                    await err_db.commit()
            raise
