"""Plain-text transactional email dispatch for verification and password
reset (transactional-email spec). No HTML template — `send_mail` only.

Recipient is always `user.email` read from the DB inside this module, never
a caller-supplied string, closing the email-header-injection surface
(design.md threat matrix).
"""
from django.conf import settings
from django.core.mail import send_mail


def _verify_link(raw_token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL}/verify-email?token={raw_token}"


def _reset_link(raw_token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL}/reset-password?token={raw_token}"


def send_verification_email(*, user, raw_token: str) -> None:
    link = _verify_link(raw_token)
    send_mail(
        subject="Verify your email",
        message=(
            "Welcome! Please verify your email address by opening the link below:\n\n"
            f"{link}\n\n"
            "If you did not create this account, you can ignore this message."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_reset_email(*, user, raw_token: str) -> None:
    link = _reset_link(raw_token)
    send_mail(
        subject="Reset your password",
        message=(
            "We received a request to reset your password. Open the link below to "
            "choose a new one:\n\n"
            f"{link}\n\n"
            "If you did not request this, you can ignore this message."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
