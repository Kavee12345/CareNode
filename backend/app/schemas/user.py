from pydantic import BaseModel, EmailStr
from datetime import datetime, date
import uuid


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    date_of_birth: date | None
    gender: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
