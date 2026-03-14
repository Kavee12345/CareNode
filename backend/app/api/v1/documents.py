import uuid
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.agent import Agent
from app.schemas.document import DocumentOut, DocumentListOut, DocumentUploadResponse
from app.services.storage_service import upload_file, get_presigned_url, delete_file
from app.tasks.document_processor import process_document
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.config import settings

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate file
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"Unsupported file type: {file.content_type}")

    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise ValidationError(f"File too large: {size_mb:.1f}MB > {settings.max_upload_size_mb}MB limit")

    # Get user's agent
    result = await db.execute(select(Agent).where(Agent.user_id == current_user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent")

    # Upload to MinIO
    doc_id = uuid.uuid4()
    minio_key = f"users/{current_user.id}/{doc_id}/{file.filename}"
    upload_file(file_bytes, minio_key, file.content_type)

    # Create DB record
    doc = Document(
        id=doc_id,
        user_id=current_user.id,
        agent_id=agent.id,
        filename=str(doc_id),
        original_name=file.filename,
        mime_type=file.content_type,
        file_size_bytes=len(file_bytes),
        minio_key=minio_key,
        processing_status="pending",
    )
    db.add(doc)
    await db.commit()

    # Queue background processing
    background_tasks.add_task(process_document, doc_id, current_user.id, agent.id)

    return DocumentUploadResponse(
        id=doc_id,
        original_name=file.filename,
        processing_status="pending",
        message="Document uploaded. Processing has started.",
    )


@router.get("", response_model=DocumentListOut)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(func.count()).where(Document.user_id == current_user.id)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    docs = result.scalars().all()

    return DocumentListOut(items=list(docs), total=total, page=page, page_size=page_size)


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document")
    return doc


@router.get("/{doc_id}/download-url")
async def get_download_url(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document")

    url = get_presigned_url(doc.minio_key, expires_seconds=900)
    return {"url": url, "expires_in": 900}


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document")

    # Delete from MinIO
    try:
        delete_file(doc.minio_key)
    except Exception:
        pass  # Don't fail if MinIO delete fails; DB cascade handles chunks

    await db.delete(doc)
    await db.commit()
