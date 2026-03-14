from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.agent import Agent
from app.models.health import RefreshToken
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from app.core.exceptions import ConflictError, UnauthorizedError
from app.config import settings


async def register_user(
    db: AsyncSession, email: str, password: str, full_name: str | None = None
) -> tuple[User, Agent]:
    """Create user + auto-provision their private agent."""
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.flush()  # get user.id without committing

    # Auto-provision private agent
    agent = Agent(user_id=user.id, name=f"{full_name or email.split('@')[0]}'s Health Agent")
    db.add(agent)
    await db.commit()
    await db.refresh(user)
    await db.refresh(agent)
    return user, agent


async def login_user(
    db: AsyncSession, email: str, password: str
) -> tuple[str, str]:
    """Authenticate and return (access_token, refresh_token)."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    access_token = create_access_token(str(user.id))
    raw_refresh, hashed_refresh = create_refresh_token()

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(rt)
    await db.commit()

    return access_token, raw_refresh


async def refresh_access_token(db: AsyncSession, raw_refresh_token: str) -> tuple[str, str]:
    """Rotate refresh token and return new (access_token, refresh_token)."""
    token_hash = hash_refresh_token(raw_refresh_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise UnauthorizedError("Invalid or expired refresh token")

    # Revoke old token
    rt.revoked = True

    # Issue new tokens
    access_token = create_access_token(str(rt.user_id))
    raw_new, hashed_new = create_refresh_token()

    new_rt = RefreshToken(
        user_id=rt.user_id,
        token_hash=hashed_new,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_rt)
    await db.commit()

    return access_token, raw_new


async def logout_user(db: AsyncSession, raw_refresh_token: str) -> None:
    """Revoke the refresh token."""
    token_hash = hash_refresh_token(raw_refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()


async def change_password(
    db: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")

    user.hashed_password = hash_password(new_password)

    # Revoke all refresh tokens
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked == False  # noqa: E712
        )
    )
    for rt in result.scalars().all():
        rt.revoked = True

    await db.commit()
