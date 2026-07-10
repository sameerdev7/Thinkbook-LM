"""
Cryptographic primitives for auth. Deliberately dependency-light and boring --
this is the one part of the app where "boring and well-understood" beats
clever:

- Passwords: bcrypt directly (not passlib -- passlib's bcrypt backend has had
  compatibility breaks with recent bcrypt releases; the `bcrypt` package
  alone is simpler and does exactly one thing).
- Access tokens: short-lived JWTs (stateless, verified without a DB hit).
- Refresh tokens & email/reset tokens: opaque random strings, stored as a
  SHA-256 hash in the DB (never store the verifiable secret itself -- same
  reasoning as password hashing, but a fast hash is fine here since these
  are high-entropy random tokens, not low-entropy user-chosen passwords).
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Literal

import bcrypt
import jwt

from app.config import settings

# ---------- Passwords ----------

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False  # malformed hash


# ---------- Opaque tokens (refresh, email verify, password reset) ----------

def generate_opaque_token() -> str:
    """High-entropy URL-safe string handed to the client. Only its hash is stored server-side."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------- JWT access tokens ----------

TokenType = Literal["access"]


def create_access_token(user_id: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> str:
    """Returns the user_id (sub claim). Raises InvalidTokenError on any problem."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Access token expired")
    except jwt.InvalidTokenError:
        raise InvalidTokenError("Invalid access token")

    if payload.get("type") != "access":
        raise InvalidTokenError("Wrong token type")
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject")
    return user_id


def refresh_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def verification_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)


def reset_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
