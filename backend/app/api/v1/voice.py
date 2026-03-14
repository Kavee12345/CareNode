import base64
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation, Message
from app.models.health import HealthEvent
from app.models.user import User
from app.schemas.chat import MessageOut
from app.schemas.voice import TTSRequest, VoiceResponse
from app.agent.medical_agent import run_medical_agent
from app.services.voice_service import transcribe_audio, synthesize_speech

router = APIRouter(prefix="/voice", tags=["voice"])

ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/mp3", "audio/mpeg",
    "audio/mp4", "audio/m4a",
    "audio/flac",
}


@router.post("/conversations/{conv_id}/messages", response_model=VoiceResponse)
async def send_voice_message(
    conv_id: uuid.UUID,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send an audio message and get a voice response from the medical agent."""
    # Validate audio file
    if audio.content_type not in ALLOWED_AUDIO_TYPES:
        raise ValidationError(f"Unsupported audio type: {audio.content_type}")

    audio_bytes = await audio.read()
    size_mb = len(audio_bytes) / (1024 * 1024)
    if size_mb > settings.voice_max_audio_size_mb:
        raise ValidationError(
            f"Audio too large: {size_mb:.1f}MB > {settings.voice_max_audio_size_mb}MB limit"
        )

    # Verify conversation ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("Conversation")

    # Step 1: Speech-to-Text
    transcript = await transcribe_audio(audio_bytes, audio.content_type)

    # Step 2: Save user message
    user_msg = Message(
        conversation_id=conv_id,
        user_id=current_user.id,
        role="user",
        content=transcript,
    )
    db.add(user_msg)
    await db.commit()

    # Update conversation title from first user message
    if conv.title == "New Conversation":
        conv.title = transcript[:80] + ("..." if len(transcript) > 80 else "")
        await db.commit()

    # Step 3: Load conversation history
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    history_msgs = list(reversed(history_result.scalars().all()))
    history_out = [MessageOut.model_validate(m) for m in history_msgs[:-1]]

    # Step 4: Run medical agent (non-streaming)
    medical_response = await run_medical_agent(
        db,
        user_id=current_user.id,
        user_message=transcript,
        conversation_history=history_out,
    )

    # Step 5: Persist assistant message
    assistant_msg = Message(
        conversation_id=conv_id,
        user_id=current_user.id,
        role="assistant",
        content=medical_response.answer,
        escalation_level=medical_response.escalation_level,
        confidence_score=medical_response.confidence,
        recommendations=medical_response.recommendations,
        disclaimer=medical_response.disclaimer,
        follow_up_questions=medical_response.follow_up_questions,
    )
    db.add(assistant_msg)

    # Auto-create health event for urgent/emergency escalations
    if medical_response.escalation_level in ("urgent", "emergency"):
        event = HealthEvent(
            user_id=current_user.id,
            event_type="symptom",
            title=f"[{medical_response.escalation_level.upper()}] {transcript[:100]}",
            description=medical_response.answer[:500],
            event_date=date.today(),
            severity="high" if medical_response.escalation_level == "emergency" else "medium",
            source_msg_id=assistant_msg.id,
        )
        db.add(event)

    await db.commit()

    # Step 6: Text-to-Speech
    tts_audio = await synthesize_speech(medical_response.answer)
    audio_b64 = base64.b64encode(tts_audio).decode("utf-8")

    return VoiceResponse(
        transcript=transcript,
        response=medical_response,
        audio_base64=audio_b64,
    )


@router.post("/tts")
async def text_to_speech(
    body: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """Convert text to speech. Useful for replaying previous messages as audio."""
    if not body.text.strip():
        raise ValidationError("Text cannot be empty")

    audio_bytes = await synthesize_speech(body.text)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=response.mp3"},
    )
