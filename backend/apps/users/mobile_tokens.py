"""Issue, resolve and revoke the mobile bearer token (GitHub #19).

Reuses `tokens.hash_token` so a raw token is never persisted: the phone keeps
the raw value, the database keeps its sha256. A token is valid only while it
is not revoked, not expired and its user is still active.
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.users.models import MobileToken, User
from apps.users.tokens import hash_token

# `last_used_at` is informational; writing it on every request would turn each
# read into a write, so it is refreshed at most this often.
_LAST_USED_GRANULARITY = timedelta(minutes=5)


def issue_mobile_token(user: User, device_name: str = "") -> tuple[str, MobileToken]:
    """Returns `(raw, token)`. The raw value goes to the phone once and is
    never stored or logged."""
    raw = secrets.token_urlsafe(32)
    token = MobileToken.objects.create(
        user=user,
        token_hash=hash_token(raw),
        device_name=device_name[:100],
        expires_at=timezone.now() + timedelta(days=settings.MOBILE_TOKEN_TTL_DAYS),
    )
    return raw, token


def resolve_mobile_token(raw: str) -> User | None:
    """The token's user, or `None` for an unknown, expired or revoked token
    or a deactivated account."""
    if not raw:
        return None
    token = MobileToken.objects.select_related("user").filter(token_hash=hash_token(raw)).first()
    now = timezone.now()
    if token is None or token.revoked_at is not None or token.expires_at <= now or not token.user.is_active:
        return None
    if token.last_used_at is None or now - token.last_used_at > _LAST_USED_GRANULARITY:
        MobileToken.objects.filter(pk=token.pk).update(last_used_at=now)
    return token.user


def revoke_mobile_token(raw: str) -> bool:
    """Revokes this one token. `False` when it was unknown or already revoked."""
    if not raw:
        return False
    revoked = MobileToken.objects.filter(token_hash=hash_token(raw), revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )
    return revoked > 0
