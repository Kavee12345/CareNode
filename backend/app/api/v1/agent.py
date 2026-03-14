from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.schemas.health import AgentOut, AgentUpdate
from app.services.vector_service import delete_all_user_chunks
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/agent", tags=["agent"])


async def _get_agent(db: AsyncSession, user_id) -> Agent:
    result = await db.execute(select(Agent).where(Agent.user_id == user_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent")
    return agent


@router.get("/me", response_model=AgentOut)
async def get_agent(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_agent(db, current_user.id)


@router.patch("/me", response_model=AgentOut)
async def update_agent(
    body: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await _get_agent(db, current_user.id)
    if body.name is not None:
        agent.name = body.name
    if body.system_prompt_override is not None:
        agent.system_prompt_override = body.system_prompt_override
    await db.commit()
    await db.refresh(agent)
    return agent


@router.post("/me/reset", status_code=204)
async def reset_agent_embeddings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all vector embeddings for this user (re-index from scratch)."""
    await delete_all_user_chunks(db, user_id=current_user.id)
    await db.commit()
