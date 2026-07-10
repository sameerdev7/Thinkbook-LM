"""
All the actual auth logic lives here, kept separate from the route handlers
in app/routers/auth.py so it's independently testable and so the tricky
part -- refresh token rotation + reuse detection -- is in one obvious place.
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session as DBSession

from app.auth.models import User, RefreshToken, EmailToken
from app.auth import security
from app.auth import email_service

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised for any auth failure the route layer should turn into a 4xx."""
    pass


# ---------- Registration / login ----------

def register_user(db: DBSession, email: str, password: str) -> User:
    email = email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise AuthError("An account with this email already exists")

    user = User(email=email, hashed_password=security.hash_password(password), is_verified=False)
    db.add(user)
    db.commit()
    db.refresh(user)

    _issue_and_send_verification_email(db, user)
    return user


def authenticate_user(db: DBSession, email: str, password: str) -> User:
    from app.config import settings

    email = email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    # Same error for "no such user" and "wrong password" -- don't leak which one.
    if not user or not security.verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password")
    if not user.is_active:
        raise AuthError("This account has been disabled")
    if settings.REQUIRE_EMAIL_VERIFICATION_TO_LOGIN and not user.is_verified:
        raise AuthError("Please verify your email before logging in")
    return user


# ---------- Token issuance / rotation ----------

def issue_token_pair(
    db: DBSession, user: User, family_id: Optional[str] = None,
    user_agent: Optional[str] = None, ip_address: Optional[str] = None,
) -> Tuple[str, str]:
    """Returns (access_token, refresh_token_plaintext). Call with family_id=None for a fresh login."""
    family_id = family_id or str(uuid.uuid4())

    refresh_plain = security.generate_opaque_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=security.hash_token(refresh_plain),
        family_id=family_id,
        expires_at=security.refresh_token_expiry(),
        user_agent=user_agent,
        ip_address=ip_address,
    ))
    db.commit()

    access_token = security.create_access_token(user.id)
    return access_token, refresh_plain


def rotate_refresh_token(
    db: DBSession, refresh_token_plain: str,
    user_agent: Optional[str] = None, ip_address: Optional[str] = None,
) -> Tuple[str, str, User]:
    """
    Validates + rotates a refresh token. On reuse of an already-used token
    (a strong signal the token was stolen and both the attacker and the
    legitimate user have now tried to use it), the ENTIRE token family is
    revoked -- every device using that login chain gets signed out, and the
    user has to log in again. This is the standard mitigation for refresh
    token theft.
    """
    token_hash = security.hash_token(refresh_token_plain)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not row:
        raise AuthError("Invalid refresh token")

    if row.revoked_at is not None:
        raise AuthError("This session has been revoked, please log in again")

    if row.used_at is not None:
        logger.warning(f"Refresh token reuse detected for user {row.user_id}, family {row.family_id} -- revoking family")
        _revoke_family(db, row.family_id)
        raise AuthError("Token reuse detected, all sessions have been signed out for your security")

    if row.expires_at <= datetime.utcnow():
        raise AuthError("Refresh token expired, please log in again")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or not user.is_active:
        raise AuthError("Account unavailable")

    row.used_at = datetime.utcnow()
    db.commit()

    access_token, new_refresh_plain = issue_token_pair(
        db, user, family_id=row.family_id, user_agent=user_agent, ip_address=ip_address,
    )
    # Link the new token back to the one it replaced (audit trail).
    new_row = db.query(RefreshToken).filter(RefreshToken.token_hash == security.hash_token(new_refresh_plain)).first()
    if new_row:
        new_row.replaces_token_id = row.id
        db.commit()

    return access_token, new_refresh_plain, user


def revoke_refresh_token(db: DBSession, refresh_token_plain: str):
    """Logout: revoke just this one token/device."""
    token_hash = security.hash_token(refresh_token_plain)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.utcnow()
        db.commit()


def revoke_all_tokens_for_user(db: DBSession, user_id: str):
    """Logout everywhere / triggered automatically on password change."""
    now = datetime.utcnow()
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": now})
    db.commit()


def _revoke_family(db: DBSession, family_id: str):
    now = datetime.utcnow()
    db.query(RefreshToken).filter(
        RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": now})
    db.commit()


# ---------- Email verification ----------

def _issue_and_send_verification_email(db: DBSession, user: User):
    plain = security.generate_opaque_token()
    db.add(EmailToken(
        user_id=user.id, token_hash=security.hash_token(plain),
        token_type="verify_email", expires_at=security.verification_token_expiry(),
    ))
    db.commit()
    try:
        email_service.send_verification_email(user.email, plain)
    except Exception as e:
        # Don't fail registration if the mail server hiccups -- user can hit "resend".
        logger.error(f"Failed to send verification email to {user.email}: {e}")


def resend_verification_email(db: DBSession, email: str):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if user and not user.is_verified:
        _issue_and_send_verification_email(db, user)
    # Always behave the same whether or not the account exists / is already verified.


def verify_email(db: DBSession, token_plain: str) -> User:
    row = _consume_email_token(db, token_plain, "verify_email")
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise AuthError("Account no longer exists")
    user.is_verified = True
    db.commit()
    return user


# ---------- Password reset ----------

def request_password_reset(db: DBSession, email: str):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user:
        return  # don't leak account existence -- route returns a generic message either way

    plain = security.generate_opaque_token()
    db.add(EmailToken(
        user_id=user.id, token_hash=security.hash_token(plain),
        token_type="reset_password", expires_at=security.reset_token_expiry(),
    ))
    db.commit()
    try:
        email_service.send_password_reset_email(user.email, plain)
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {e}")


def reset_password(db: DBSession, token_plain: str, new_password: str) -> User:
    row = _consume_email_token(db, token_plain, "reset_password")
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise AuthError("Account no longer exists")

    user.hashed_password = security.hash_password(new_password)
    db.commit()
    # Password changed -- assume compromise scenario, sign the user out everywhere.
    revoke_all_tokens_for_user(db, user.id)
    return user


def change_password(db: DBSession, user: User, current_password: str, new_password: str):
    if not security.verify_password(current_password, user.hashed_password):
        raise AuthError("Current password is incorrect")
    user.hashed_password = security.hash_password(new_password)
    db.commit()
    revoke_all_tokens_for_user(db, user.id)


def _consume_email_token(db: DBSession, token_plain: str, expected_type: str) -> EmailToken:
    token_hash = security.hash_token(token_plain)
    row = db.query(EmailToken).filter(EmailToken.token_hash == token_hash).first()
    if not row or row.token_type != expected_type:
        raise AuthError("Invalid or expired token")
    if not row.is_valid:
        raise AuthError("Invalid or expired token")
    row.used_at = datetime.utcnow()
    db.commit()
    return row
