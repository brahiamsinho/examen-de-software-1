"""Who gets a push, and getting it out without ever hurting the request that caused it."""
import logging
import threading
import time
from collections.abc import Callable

from django.core.cache import cache

from apps.notifications import fcm
from apps.notifications.models import DeviceToken
from apps.organizations.models import Membership

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 2.0
# A busy diagram changes many times a minute; one push per diagram per window.
DOCUMENT_PUSH_WINDOW_SECONDS = 60


def register_device(*, user, token: str, platform: str) -> None:
    # A token identifies a phone, and the phone belongs to whoever logged in last.
    DeviceToken.objects.update_or_create(token=token, defaults={"user": user, "platform": platform})


def unregister_device(*, user, token: str) -> None:
    DeviceToken.objects.filter(token=token, user=user).delete()


def _run_in_background(job: Callable[[], None]) -> None:
    threading.Thread(target=job, daemon=True).start()


def _member_tokens(organization_id, exclude_user_id) -> list[str]:
    # Membership is read now, at send time, so someone removed from the
    # organization stops receiving its pushes immediately.
    user_ids = list(
        Membership.all_objects.filter(organization_id=organization_id).values_list("user_id", flat=True)
    )
    if exclude_user_id is not None:
        user_ids = [user_id for user_id in user_ids if user_id != exclude_user_id]
    if not user_ids:
        return []
    return list(DeviceToken.objects.filter(user_id__in=user_ids).values_list("token", flat=True))


def _deliver(tokens: list[str], title: str, body: str, data: dict) -> None:
    pending = list(tokens)
    for attempt in range(MAX_ATTEMPTS):
        result = fcm.send(pending, title=title, body=body, data=data)
        if result.invalid:
            DeviceToken.objects.filter(token__in=result.invalid).delete()
        pending = result.retry
        if not pending:
            return
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(_BACKOFF_SECONDS * (attempt + 1))
    logger.warning("Push gave up on %d device(s) after %d attempts", len(pending), MAX_ATTEMPTS)


def notify_organization(*, organization_id, title: str, body: str, data: dict, exclude_user_id=None) -> None:
    """Pushes to every phone of the organization's members. Never raises: a push
    is a courtesy and must not fail the request that triggered it."""
    try:
        if not fcm.is_configured():
            return
        tokens = _member_tokens(organization_id, exclude_user_id)
        if not tokens:
            return
        _run_in_background(lambda: _safe_deliver(tokens, title, body, data))
    except Exception:  # noqa: BLE001 - see docstring
        logger.exception("Could not queue a push notification")


def _safe_deliver(tokens: list[str], title: str, body: str, data: dict) -> None:
    try:
        _deliver(tokens, title, body, data)
    except Exception:  # noqa: BLE001 - runs in a thread nobody awaits
        logger.exception("Push delivery failed")


def document_push_allowed(document_id) -> bool:
    """True for the first change of a diagram in each window (atomic `add`)."""
    return cache.add(f"push:document:{document_id}", 1, DOCUMENT_PUSH_WINDOW_SECONDS)
