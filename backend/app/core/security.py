"""Security helpers: password hashing and JWT creation/verification."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from .config import settings


def _truncate(secret: str) -> bytes:
    """bcrypt has a 72-byte limit — truncate cleanly in UTF-8."""
    return secret.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_truncate(password), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str | int, expires_delta: Optional[timedelta] = None, extra: Optional[dict[str, Any]] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(UTC) + expires_delta
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
