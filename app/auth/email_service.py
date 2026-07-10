"""
Minimal SMTP email sender. Works with any provider (Gmail app passwords,
SendGrid/Resend/Postmark SMTP relays, your own mail server) since it's just
env-configured SMTP -- no vendor SDK lock-in.

If SMTP isn't configured (no host/user/password in .env), emails are logged
to the console instead of raising, so registration/reset flows are testable
locally without setting up real email delivery.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, html_body: str, text_body: str):
    if not settings.email_configured:
        logger.info(
            "SMTP not configured -- logging email instead of sending.\n"
            f"TO: {to_email}\nSUBJECT: {subject}\nBODY:\n{text_body}"
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())


def send_verification_email(to_email: str, token: str):
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    _send(
        to_email,
        "Verify your ThinkbookLM account",
        html_body=f'<p>Welcome to ThinkbookLM. <a href="{link}">Click here to verify your email</a>. '
                   f'This link expires in {settings.VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>',
        text_body=f"Welcome to ThinkbookLM. Verify your email: {link} "
                   f"(expires in {settings.VERIFICATION_TOKEN_EXPIRE_HOURS} hours)",
    )


def send_password_reset_email(to_email: str, token: str):
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    _send(
        to_email,
        "Reset your ThinkbookLM password",
        html_body=f'<p>Someone requested a password reset for this account. '
                   f'<a href="{link}">Click here to set a new password</a>. '
                   f'This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes. '
                   f'If this wasn\'t you, ignore this email.</p>',
        text_body=f"Reset your password: {link} "
                   f"(expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes). "
                   f"If this wasn't you, ignore this email.",
    )
