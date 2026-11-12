from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from ..models.enums import UserRole


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    full_name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., pattern=r"^\+?998\d{9}$")
    email: Optional[str] = None


class UserRegister(UserBase):
    password: Optional[str] = Field(None, min_length=6)
    telegram_id: Optional[int] = None
    role: UserRole = UserRole.CITIZEN


class UserLogin(BaseModel):
    phone: str
    password: str


class UserOut(UserBase):
    id: int
    telegram_id: Optional[int] = None
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
