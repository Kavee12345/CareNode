from pydantic import BaseModel
from datetime import datetime
import uuid
from typing import Literal, List, Optional


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListOut(BaseModel):
    items: List[ConversationOut]
    total: int


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    escalation_level: Optional[str]
    confidence_score: Optional[float]
    recommendations: Optional[List[str]]
    disclaimer: Optional[str]
    follow_up_questions: Optional[List[str]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailOut(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    messages: List[MessageOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str


class MedicalResponse(BaseModel):
    """Structured response from the medical agent."""
    answer: str
    escalation_level: Literal["none", "mild", "urgent", "emergency"] = "none"
    confidence: float = 0.8
    recommendations: List[str] = []
    disclaimer: str = "This information is for educational purposes only. Always consult a qualified healthcare professional for medical advice."
    sources: List[str] = []
    follow_up_questions: List[str] = []
