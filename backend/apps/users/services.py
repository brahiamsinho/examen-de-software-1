"""Invariant-bearing operations for the users domain.

HTTP-agnostic, keyword-only, raising `errors.py` exceptions. Transaction
boundaries live here, not in views, so a later Channels consumer or
management command can call these functions directly.
"""
import time
from datetime import timedelta

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.organizations.services import create_organization, derive_workspace_name, generate_unique_slug
from apps.users.emails import send_reset_email, send_verification_email
from apps.users.errors import (
    DuplicateEmailError,
    InvalidCredentialsError,
    PasswordPolicyError,
    ResendCooldownError,
    ResendRateLimitError,
    TokenExpiredError,
    TokenInvalidError,
    TokenUsedError,
)
from apps.users.models import EmailToken, User
from apps.users.tokens import issue_token, resolve_token

_RESEND_COOLDOWN_SECONDS = 60
_RESEND_HOURLY_CAP = 5

# Anti-enumeration timing parity (design.md DD4 / Open Questions
# "Timing-parity limit"): applied on the miss/throttled paths of
# `request_password_reset` only, to approximate — not eliminate — the
# response time of the hit path's real SMTP send.
_RESET_ANTI_ENUMERATION_DELAY_SECONDS = 0.3


@transaction.atomic
def register_user(*, email: str, password: str, full_name: str = "") -> User:
    """Create a `User`, after validating the password against the project's
    configured password validators, and provision exactly one `Organization`
    with the new user as `OWNER` in the same transaction (user-authentication
    spec: "Registration Provisions One Organization"; design.md DD2). If
    organization provisioning fails, the whole transaction rolls back — no
    `User` row may persist without its organization.
    """
    from django.contrib.auth.password_validation import validate_password

    normalized_email = User.objects.normalize_email(email)
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise DuplicateEmailError(f"A user with email '{email}' already exists.")

    try:
        validate_password(password)
    except ValidationError as exc:
        raise PasswordPolicyError("; ".join(exc.messages)) from exc

    try:
        user = User.objects.create_user(email=email, password=password, full_name=full_name)
    except IntegrityError as exc:
        raise DuplicateEmailError(f"A user with email '{email}' already exists.") from exc

    source = full_name.strip() or normalized_email.split("@", 1)[0]
    create_organization(
        owner=user,
        name=derive_workspace_name(source=source),
        slug=generate_unique_slug(source=source),
    )

    raw_token, _token = issue_token(user, "verify")
    transaction.on_commit(lambda: send_verification_email(user=user, raw_token=raw_token))

    return user


def authenticate_user(*, email: str, password: str) -> User:
    """Authenticate by email/password. Raises one generic error for both
    an unknown email and a wrong password (user-authentication spec: no
    email enumeration).
    """
    user = authenticate(username=email, password=password)
    if user is None:
        raise InvalidCredentialsError("Invalid email or password.")
    return user


def verify_email(*, token: str) -> User:
    """Consumes a verification token: marks it used and flips
    `User.is_verified` (email-verification spec § "Verification Token
    Consumption").
    """
    email_token = resolve_token(token, "verify")
    if email_token is None:
        raise TokenInvalidError("This verification link is invalid.")
    if email_token.used_at is not None:
        raise TokenUsedError("This verification link was already used.")
    if email_token.expires_at < timezone.now():
        raise TokenExpiredError("This verification link has expired.")

    user = email_token.user
    user.is_verified = True
    user.save(update_fields=["is_verified"])

    email_token.used_at = timezone.now()
    email_token.save(update_fields=["used_at"])

    return user


def _cooldown_active(*, user: User, purpose: str) -> bool:
    """Shared throttle query (design.md DD3): the same cooldown/cap check
    backs both `resend_verification` and `request_password_reset`'s
    throttle branch — one table already stores exactly the needed
    timestamp, so no cache/middleware throttle is needed.
    """
    last = EmailToken.objects.filter(user=user, purpose=purpose).order_by("-created_at").first()
    return last is not None and last.created_at >= timezone.now() - timedelta(
        seconds=_RESEND_COOLDOWN_SECONDS
    )


def _hourly_cap_reached(*, user: User, purpose: str) -> bool:
    return (
        EmailToken.objects.filter(
            user=user, purpose=purpose, created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        >= _RESEND_HOURLY_CAP
    )


def resend_verification(*, user: User) -> None:
    """Issues and emails a new verification token, subject to a 60s cooldown
    and a 5-per-rolling-hour cap (email-verification spec § "Resend
    Verification with Cooldown and Hourly Cap"; design.md DD3).
    """
    if _cooldown_active(user=user, purpose="verify"):
        raise ResendCooldownError("Please wait before requesting another verification email.")
    if _hourly_cap_reached(user=user, purpose="verify"):
        raise ResendRateLimitError("Too many verification emails requested. Try again later.")

    raw_token, _token = issue_token(user, "verify")
    transaction.on_commit(lambda: send_verification_email(user=user, raw_token=raw_token))


def request_password_reset(*, email: str) -> None:
    """Never raises and never branches visibly to the caller (design.md
    DD4): every path — existing account, non-existing account, or throttled
    account — returns `None`. The miss and throttled paths additionally
    sleep a fixed delay first, to approximate (not eliminate) the response
    time of the hit path's real SMTP send (password-reset spec § "Fixed
    timing-parity delay").
    """
    normalized_email = User.objects.normalize_email(email)
    try:
        user = User.objects.get(email__iexact=normalized_email)
    except User.DoesNotExist:
        time.sleep(_RESET_ANTI_ENUMERATION_DELAY_SECONDS)
        return None

    if _cooldown_active(user=user, purpose="reset") or _hourly_cap_reached(user=user, purpose="reset"):
        time.sleep(_RESET_ANTI_ENUMERATION_DELAY_SECONDS)
        return None

    raw_token, _token = issue_token(user, "reset")
    transaction.on_commit(lambda: send_reset_email(user=user, raw_token=raw_token))
    return None


def confirm_password_reset(*, token: str, new_password: str) -> User:
    """Consumes a reset token: validates the new password, updates it,
    marks the token used, invalidates every other outstanding reset token
    for that user, and sets `is_verified = True` (password-reset spec §
    "Confirm Reset").
    """
    from django.contrib.auth.password_validation import validate_password

    email_token = resolve_token(token, "reset")
    if email_token is None:
        raise TokenInvalidError("This reset link is invalid.")
    if email_token.used_at is not None:
        raise TokenUsedError("This reset link was already used.")
    if email_token.expires_at < timezone.now():
        raise TokenExpiredError("This reset link has expired.")

    user = email_token.user

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        raise PasswordPolicyError("; ".join(exc.messages)) from exc

    user.set_password(new_password)
    user.is_verified = True
    user.save(update_fields=["password", "is_verified"])

    now = timezone.now()
    email_token.used_at = now
    email_token.save(update_fields=["used_at"])

    EmailToken.objects.filter(user=user, purpose="reset", used_at__isnull=True).exclude(
        pk=email_token.pk
    ).update(used_at=now)

    return user
