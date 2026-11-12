"""Auth endpoints: register, login, token."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...core.security import hash_password, verify_password, create_access_token
from ...models.models import User
from ...models.enums import UserRole
from ...schemas.user import UserRegister, UserLogin, UserOut, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    # Uniqueness by phone
    existing = (await db.execute(select(User).where(User.phone == payload.phone))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Bu telefon raqam allaqachon ro'yxatdan o'tgan")
    pw_hash = hash_password(payload.password) if payload.password else None
    user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        telegram_id=payload.telegram_id,
        role=payload.role,
        password_hash=pw_hash,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id, extra={"role": user.role.value})
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.phone == payload.phone))).scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Telefon yoki parol noto'g'ri")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Foydalanuvchi bloklangan")
    token = create_access_token(user.id, extra={"role": user.role.value})
    return TokenOut(access_token=token, user=UserOut.model_validate(user))
