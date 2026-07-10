"""
Auth data model.

RefreshToken uses a "family" pattern for rotation + reuse detection:
- Every login/refresh issues a new refresh token belonging to a `family_id`.
- On refresh, the OLD token is marked used_at and the NEW token points to it
  via `replaces_token_id`, keeping the same `family_id`.
- If a token with `used_at` already set is presented again (a stolen/replayed
  token), that's a signal of compromise -- the ENTIRE family is revoked, not
  just that one token, forcing a re-login. This is the same pattern used by
  Auth0 / Firebase / most production refresh-token systems.

Tokens are stored as SHA-256 hashes, never in plaintext, same as passwords.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(320), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)

    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)  # for admin-disabling an account

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("NotebookSession", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    token_hash = Column(String(64), unique=True, nullable=False, index=True)  # sha256 hex digest
    family_id = Column(String(36), nullable=False, index=True)
    replaces_token_id = Column(String(36), nullable=True)

    issued_at = Column(DateTime, default=_now)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)      # set once rotated/consumed
    revoked_at = Column(DateTime, nullable=True)   # set on logout, family revocation, or password change

    user_agent = Column(String(256), nullable=True)
    ip_address = Column(String(64), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.revoked_at is None and self.expires_at > _now()


class EmailToken(Base):
    """Single-use tokens for email verification and password reset."""
    __tablename__ = "email_tokens"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_type = Column(String(32), nullable=False)  # "verify_email" | "reset_password"

    created_at = Column(DateTime, default=_now)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > _now()
