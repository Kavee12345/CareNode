from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token payload")
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    # Set RLS context — SET LOCAL doesn't support bind params, UUID is safe to inline
    await db.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user
