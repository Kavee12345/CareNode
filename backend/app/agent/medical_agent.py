"""
Core medical agent using LangChain + Gemini.

Architecture:
  1. Embed user query
  2. Retrieve top-k relevant chunks from user's private vector store
  3. Build context-aware prompt
  4. Stream Gemini response
  5. Parse structured MedicalResponse
  6. Return with escalation level
"""
import uuid
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from app.config import settings
from app.services.vector_service import similarity_search
from app.agent.system_prompt import MEDICAL_SYSTEM_PROMPT
from app.agent.output_parser import parse_medical_response
from app.schemas.chat import MedicalResponse, MessageOut


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        max_output_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
    )


def _build_context_block(chunks: list[dict]) -> str:
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


def _build_history_block(history: list[MessageOut]) -> list:
    """Convert conversation history to LangChain message objects."""
    lc_messages = []
    for msg in history[-10:]:  # Last 10 messages for context window efficiency
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages


async def run_medical_agent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_message: str,
    conversation_history: list[MessageOut],
) -> MedicalResponse:
    """
    Run the medical agent synchronously and return a MedicalResponse.
    Used for non-streaming endpoints.
    """
    # 1. Retrieve relevant chunks (zero-leak: always scoped to user_id)
    chunks = await similarity_search(db, user_id=user_id, query=user_message)

    # 2. Build prompt
    context_block = _build_context_block(chunks)
    history_messages = _build_history_block(conversation_history)

    user_prompt = f"""{context_block}

=== User Question ===
{user_message}

Respond ONLY with a valid JSON object matching the schema in your instructions."""

    messages = [
        SystemMessage(content=MEDICAL_SYSTEM_PROMPT),
        *history_messages,
        HumanMessage(content=user_prompt),
    ]

    # 3. Call Gemini
    llm = _get_llm()
    response = await llm.ainvoke(messages)
    raw_text = response.content

    # 4. Parse structured response
    medical_response = parse_medical_response(raw_text, user_message)

    # 5. Attach source document names
    medical_response.sources = list({
        c.get("metadata", {}).get("original_filename", "Health record")
        for c in chunks
    })

    return medical_response


async def stream_medical_agent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_message: str,
    conversation_history: list[MessageOut],
) -> AsyncGenerator[str, None]:
    """
    Stream the medical agent response as SSE-compatible text chunks.
    Yields raw text chunks; the final structured response is sent as a
    special [DONE] event with JSON payload.
    """
    # 1. Retrieve relevant chunks
    chunks = await similarity_search(db, user_id=user_id, query=user_message)

    # 2. Build prompt
    context_block = _build_context_block(chunks)
    history_messages = _build_history_block(conversation_history)

    user_prompt = f"""{context_block}

=== User Question ===
{user_message}

Respond ONLY with a valid JSON object matching the schema in your instructions."""

    messages = [
        SystemMessage(content=MEDICAL_SYSTEM_PROMPT),
        *history_messages,
        HumanMessage(content=user_prompt),
    ]

    # 3. Stream from Gemini
    llm = _get_llm()
    full_response = ""

    async for chunk in llm.astream(messages):
        text_chunk = chunk.content
        if text_chunk:
            full_response += text_chunk
            yield f"data: {text_chunk}\n\n"

    # 4. Parse and send final structured response
    medical_response = parse_medical_response(full_response, user_message)
    medical_response.sources = list({
        c.get("metadata", {}).get("original_filename", "Health record")
        for c in chunks
    })

    import json
    yield f"data: [DONE]{json.dumps(medical_response.model_dump())}\n\n"
