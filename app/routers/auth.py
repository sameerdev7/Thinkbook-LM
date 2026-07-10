from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.auth import service
from app.auth.models import User
from app.auth.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, LogoutRequest,
    UserOut, VerifyEmailRequest, ResendVerificationRequest, ForgotPasswordRequest,
    ResetPasswordRequest, ChangePasswordRequest, MessageResponse,
)
from app.database import get_db
from app.deps import get_current_user
from app.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_meta(request: Request):
    return request.headers.get("user-agent", "")[:256], (request.client.host if request.client else None)


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("5/hour")
def register(request: Request, payload: RegisterRequest, db: DBSession = Depends(get_db)):
    try:
        user = service.register_user(db, payload.email, payload.password)
    except service.AuthError as e:
        raise HTTPException(status_code=409, detail=str(e))

    ua, ip = _client_meta(request)
    access, refresh = service.issue_token_pair(db, user, user_agent=ua, ip_address=ip)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: DBSession = Depends(get_db)):
    try:
        user = service.authenticate_user(db, payload.email, payload.password)
    except service.AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

    ua, ip = _client_meta(request)
    access, refresh = service.issue_token_pair(db, user, user_agent=ua, ip_address=ip)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
def refresh(request: Request, payload: RefreshRequest, db: DBSession = Depends(get_db)):
    try:
        ua, ip = _client_meta(request)
        access, refresh_token, _user = service.rotate_refresh_token(db, payload.refresh_token, user_agent=ua, ip_address=ip)
    except service.AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return TokenResponse(access_token=access, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, db: DBSession = Depends(get_db)):
    service.revoke_refresh_token(db, payload.refresh_token)
    return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(current_user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    service.revoke_all_tokens_for_user(db, current_user.id)
    return MessageResponse(message="Logged out on all devices")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: DBSession = Depends(get_db)):
    try:
        service.verify_email(db, payload.token)
    except service.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MessageResponse(message="Email verified")


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("3/hour")
def resend_verification(request: Request, payload: ResendVerificationRequest, db: DBSession = Depends(get_db)):
    service.resend_verification_email(db, payload.email)
    # Same response whether or not the account exists / is already verified -- avoids email enumeration.
    return MessageResponse(message="If that account exists and isn't verified yet, a new email has been sent")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("5/hour")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: DBSession = Depends(get_db)):
    service.request_password_reset(db, payload.email)
    return MessageResponse(message="If that account exists, a password reset email has been sent")


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("10/hour")
def reset_password(request: Request, payload: ResetPasswordRequest, db: DBSession = Depends(get_db)):
    try:
        service.reset_password(db, payload.token, payload.new_password)
    except service.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MessageResponse(message="Password reset -- please log in again")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    try:
        service.change_password(db, current_user, payload.current_password, payload.new_password)
    except service.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MessageResponse(message="Password changed -- please log in again on other devices")
