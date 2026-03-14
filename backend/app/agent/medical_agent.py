"""
Core medical agent using LangChain + Gemini.

Architecture:
  1. Embed user query
  2. Retrieve top-k relevant chunks from user's private vector store
  3. Build context-aware prompt
  4. Stream natural-language response
  5. Extract metadata (escalation, follow-ups) after streaming
"""
import json
import re
import uuid
from typing import AsyncGenerator, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from sqlalchemy import select

from app.config import settings
from app.services.vector_service import similarity_search
from app.agent.system_prompt import MEDICAL_SYSTEM_PROMPT
from app.agent.output_parser import extract_escalation, extract_follow_ups
from app.schemas.chat import MedicalResponse, MessageOut
from app.models.health import UserHealthNote


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        max_output_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
    )


def _build_context_block(chunks: list) -> str:
    """Format retrieved chunks as a readable context section."""
    if not chunks:
        return "No relevant health records found for this query."

    parts = ["=== Retrieved Health Records ==="]
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        filename = meta.get("original_filename", "Unknown document")
        doc_type = meta.get("doc_type", "")
        score = chunk.get("score", 0)
        parts.append(
            f"\n[Record {i} | {filename} | {doc_type} | relevance: {score:.2f}]\n{chunk['chunk_text']}"
        )
    return "\n".join(parts)


def _build_history_block(history: List[MessageOut]) -> list:
    """Convert conversation history to LangChain message objects."""
    lc_messages = []
    for msg in history[-10:]:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages


def _build_notes_block(notes: list) -> str:
    """Format user health notes as context."""
    if not notes:
        return ""
    parts = ["\n=== What You Know About This Patient ==="]
    for note in notes:
        parts.append(f"- [{note.category}] {note.note}")
    return "\n".join(parts)


def _build_user_prompt(context_block: str, notes_block: str, user_message: str) -> str:
    prompt = context_block
    if notes_block:
        prompt += notes_block
    prompt += f"\n\n=== User Says ===\n{user_message}"
    return prompt


def _parse_answer_and_followups(full_text: str) -> tuple:
    """Split response into answer text and follow-up questions."""
    # Split on --- separator
    parts = re.split(r'\n---\s*\n', full_text, maxsplit=1)
    answer = parts[0].strip()
    follow_ups: List[str] = []

    if len(parts) > 1:
        for line in parts[1].strip().splitlines():
            line = line.strip()
            if line.startswith("- "):
                follow_ups.append(line[2:].strip())
            elif line.startswith("* "):
                follow_ups.append(line[2:].strip())
            elif line:
                follow_ups.append(line)

    return answer, follow_ups


async def run_medical_agent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_message: str,
    conversation_history: List[MessageOut],
) -> MedicalResponse:
    """
    Run the medical agent and return a MedicalResponse.
    Used for non-streaming endpoints (e.g., voice).
    """
    chunks = await similarity_search(db, user_id=user_id, query=user_message)
    context_block = _build_context_block(chunks)
    history_messages = _build_history_block(conversation_history)

    # Load saved health notes about this user
    notes_result = await db.execute(
        select(UserHealthNote)
        .where(UserHealthNote.user_id == user_id, UserHealthNote.is_active == True)
        .order_by(UserHealthNote.updated_at.desc())
        .limit(20)
    )
    notes = list(notes_result.scalars().all())
    notes_block = _build_notes_block(notes)

    messages = [
        SystemMessage(content=MEDICAL_SYSTEM_PROMPT),
        *history_messages,
        HumanMessage(content=_build_user_prompt(context_block, notes_block, user_message)),
    ]

    llm = _get_llm()
    response = await llm.ainvoke(messages)
    raw_text = response.content

    answer, follow_ups = _parse_answer_and_followups(raw_text)
    escalation = extract_escalation(user_message + " " + answer)

    sources = list({
        c.get("metadata", {}).get("original_filename", "Health record")
        for c in chunks
    })

    return MedicalResponse(
        answer=answer,
        escalation_level=escalation,
        confidence=0.85,
        recommendations=[],
        disclaimer="This is for informational purposes only. Always consult a qualified healthcare professional.",
        sources=sources,
        follow_up_questions=follow_ups,
    )


async def stream_medical_agent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_message: str,
    conversation_history: List[MessageOut],
) -> AsyncGenerator[str, None]:
    """
    Stream the medical agent response as SSE text chunks.
    The LLM responds in natural language (no JSON), so chunks
    are streamed directly to the client for instant display.
    """
    chunks = await similarity_search(db, user_id=user_id, query=user_message)
    context_block = _build_context_block(chunks)
    history_messages = _build_history_block(conversation_history)

    # Load saved health notes about this user
    notes_result = await db.execute(
        select(UserHealthNote)
        .where(UserHealthNote.user_id == user_id, UserHealthNote.is_active == True)
        .order_by(UserHealthNote.updated_at.desc())
        .limit(20)
    )
    notes = list(notes_result.scalars().all())
    notes_block = _build_notes_block(notes)

    messages = [
        SystemMessage(content=MEDICAL_SYSTEM_PROMPT),
        *history_messages,
        HumanMessage(content=_build_user_prompt(context_block, notes_block, user_message)),
    ]

    llm = _get_llm()
    full_response = ""

    async for chunk in llm.astream(messages):
        text_chunk = chunk.content
        if text_chunk:
            full_response += text_chunk
            yield f"data: {text_chunk}\n\n"

    # After streaming completes, extract metadata
    answer, follow_ups = _parse_answer_and_followups(full_response)
    escalation = extract_escalation(user_message + " " + answer)

    sources = list({
        c.get("metadata", {}).get("original_filename", "Health record")
        for c in chunks
    })

    medical_response = MedicalResponse(
        answer=answer,
        escalation_level=escalation,
        confidence=0.85,
        recommendations=[],
        disclaimer="This is for informational purposes only. Always consult a qualified healthcare professional.",
        sources=sources,
        follow_up_questions=follow_ups,
    )

    yield f"data: [DONE]{json.dumps(medical_response.model_dump())}\n\n"
