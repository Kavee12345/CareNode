from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    original_name: str
    mime_type: str
    file_size_bytes: Optional[int]
    doc_type: Optional[str]
    processing_status: str
    processing_error: Optional[str]
    page_count: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    original_name: str
    processing_status: str
    message: str
