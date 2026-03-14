from pydantic import BaseModel
from datetime import datetime
import uuid
from typing import Literal


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListOut(BaseModel):
    items: list[ConversationOut]
    total: int


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    escalation_level: str | None
    confidence_score: float | None
    recommendations: list[str] | None
    disclaimer: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailOut(BaseModel):
    id: uuid.UUID
    title: str | None
    messages: list[MessageOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str


class MedicalResponse(BaseModel):
    """Structured response from the medical agent."""
    answer: str
    escalation_level: Literal["none", "mild", "urgent", "emergency"] = "none"
    confidence: float = 0.8
    recommendations: list[str] = []
    disclaimer: str = "This information is for educational purposes only. Always consult a qualified healthcare professional for medical advice."
    sources: list[str] = []
