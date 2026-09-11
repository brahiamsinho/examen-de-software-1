"""Token issuance/hashing/resolution for email verification and password
reset (design.md DD1).

`token_hash = sha256(raw).hexdigest()`, `unique=True` on `EmailToken.token_hash`
gives an O(1) indexed lookup. The raw token (`secrets.token_urlsafe(32)`, 256
bits of CSPRNG entropy) is never persisted or logged — only its hash is.
"""
import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone

from apps.users.models import EmailToken, User

_EXPIRY_HOURS: dict[str, int] = {
    "verify": 24,
    "reset": 1,
}


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_token(user: User, purpose: str) -> tuple[str, EmailToken]:
    """Creates a new `EmailToken` row and returns `(raw, token)`. The raw
    value is returned only so the caller can put it in the email link/body —
    it is never stored.
    """
    raw = secrets.token_urlsafe(32)
    hours = _EXPIRY_HOURS[purpose]
    token = EmailToken.objects.create(
        user=user,
        purpose=purpose,
        token_hash=hash_token(raw),
        expires_at=timezone.now() + timedelta(hours=hours),
    )
    return raw, token


def resolve_token(raw: str, purpose: str) -> EmailToken | None:
    """Looks up an `EmailToken` by its hash + purpose. Returns `None` when no
    row matches — callers decide how to map that to a domain error.
    """
    return EmailToken.objects.filter(token_hash=hash_token(raw), purpose=purpose).first()
