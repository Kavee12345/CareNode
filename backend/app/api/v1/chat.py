import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.conversation import Conversation, Message
from app.models.health import HealthEvent, UserHealthNote
from app.schemas.chat import (
    ConversationOut, ConversationListOut, ConversationDetailOut,
    MessageOut, ChatRequest, MedicalResponse,
)
from app.agent.medical_agent import stream_medical_agent
from app.core.exceptions import NotFoundError
from datetime import date, datetime, timezone

router = APIRouter(prefix="/chat", tags=["chat"])

# Keywords that indicate the user is sharing health-relevant info
HEALTH_NOTE_INDICATORS = {
    "symptom": [
        "i have", "i feel", "i'm feeling", "i am feeling", "my head",
        "pain in", "hurts", "aching", "nausea", "dizzy", "tired",
        "fatigue", "can't sleep", "insomnia", "fever", "cough",
        "breathing", "swelling", "rash", "itching", "bleeding",
    ],
    "medication": [
        "i take", "i'm taking", "i am taking", "prescribed",
        "medication", "medicine", "supplement", "vitamin", "dose",
        "stopped taking", "started taking",
    ],
    "lifestyle": [
        "i exercise", "i don't exercise", "i smoke", "i drink",
        "my diet", "i eat", "i sleep", "hours of sleep",
        "stress", "i work", "sedentary",
    ],
    "allergy": [
        "allergic", "allergy", "react to", "intolerant",
    ],
    "condition": [
        "diagnosed with", "i have diabetes", "i have hypertension",
        "i have asthma", "history of", "chronic", "condition",
    ],
}


def _detect_health_note_category(text: str) -> Optional[str]:
    """Check if user message contains health-relevant info worth saving."""
    text_lower = text.lower()
    # Skip very short messages or greetings
    if len(text_lower.split()) < 4:
        return None
    for category, keywords in HEALTH_NOTE_INDICATORS.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return None


async def _get_user_agent(db: AsyncSession, user_id: uuid.UUID) -> Agent:
    result = await db.execute(select(Agent).where(Agent.user_id == user_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent")
    return agent


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _get_user_agent(db, current_user.id)
    conv = Conversation(user_id=current_user.id, agent_id=agent.id, title="New Conversation")
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations", response_model=ConversationListOut)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(func.count()).where(Conversation.user_id == current_user.id)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    conversations = result.scalars().all()
    return ConversationListOut(items=list(conversations), total=total)


@router.get("/conversations/{conv_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conv_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("Conversation")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return ConversationDetailOut(
        id=conv.id,
        title=conv.title,
        messages=list(messages),
        created_at=conv.created_at,
    )


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("Conversation")
    await db.delete(conv)
    await db.commit()


@router.post("/conversations/{conv_id}/messages")
async def send_message(
    conv_id: uuid.UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get a streaming SSE response from the medical agent."""
    # Verify conversation ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("Conversation")

    # Save user message
    user_msg = Message(
        conversation_id=conv_id,
        user_id=current_user.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # Save health note if user shared health-relevant info
    note_category = _detect_health_note_category(body.message)
    if note_category:
        health_note = UserHealthNote(
            user_id=current_user.id,
            category=note_category,
            note=body.message.strip(),
            source_message_id=user_msg.id,
        )
        db.add(health_note)
        await db.commit()

    # Update conversation title from first user message
    if conv.title == "New Conversation":
        conv.title = body.message[:80] + ("..." if len(body.message) > 80 else "")
        await db.commit()

    # Load conversation history for context
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    history_msgs = list(reversed(history_result.scalars().all()))
    history_out = [MessageOut.model_validate(m) for m in history_msgs[:-1]]  # exclude current msg

    async def event_stream():
        final_data: Optional[MedicalResponse] = None

        async for chunk in stream_medical_agent(
            db,
            user_id=current_user.id,
            user_message=body.message,
            conversation_history=history_out,
        ):
            if chunk.startswith("data: [DONE]"):
                json_str = chunk[len("data: [DONE]"):].strip()
                try:
                    final_data = MedicalResponse(**json.loads(json_str))
                except Exception:
                    pass
            yield chunk

        # Persist assistant message
        if final_data:
            assistant_msg = Message(
                conversation_id=conv_id,
                user_id=current_user.id,
                role="assistant",
                content=final_data.answer,
                escalation_level=final_data.escalation_level,
                confidence_score=final_data.confidence,
                recommendations=final_data.recommendations,
                disclaimer=final_data.disclaimer,
                follow_up_questions=final_data.follow_up_questions,
            )
            db.add(assistant_msg)

            # Auto-create health event for urgent/emergency escalations
            if final_data.escalation_level in ("urgent", "emergency"):
                event = HealthEvent(
                    user_id=current_user.id,
                    event_type="symptom",
                    title=f"[{final_data.escalation_level.upper()}] {body.message[:100]}",
                    description=final_data.answer[:500],
                    event_date=date.today(),
                    severity="high" if final_data.escalation_level == "emergency" else "medium",
                    source_msg_id=assistant_msg.id,
                )
                db.add(event)

            await db.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
