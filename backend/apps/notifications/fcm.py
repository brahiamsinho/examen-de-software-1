"""The only place that talks to Firebase Cloud Messaging.

Credentials come from `FIREBASE_CREDENTIALS_PATH` (a service-account file kept
outside version control). Without it every function here is inert, so local
development and tests never need Firebase.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from django.conf import settings

logger = logging.getLogger(__name__)

_app = None


@dataclass
class SendResult:
    # Tokens Firebase says will never work again (uninstalled app, rotated token).
    invalid: list[str] = field(default_factory=list)
    # Tokens that failed for a reason worth trying again (outage, throttling).
    retry: list[str] = field(default_factory=list)


def is_configured() -> bool:
    path = settings.FIREBASE_CREDENTIALS_PATH
    return bool(path) and Path(path).is_file()


def _firebase_app():
    global _app
    if _app is None:
        import firebase_admin
        from firebase_admin import credentials

        _app = firebase_admin.initialize_app(credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH))
    return _app


def send(tokens: Sequence[str], *, title: str, body: str, data: dict[str, str]) -> SendResult:
    from firebase_admin import exceptions, messaging

    result = SendResult()
    message = messaging.MulticastMessage(
        tokens=list(tokens),
        notification=messaging.Notification(title=title, body=body),
        data={key: str(value) for key, value in data.items()},
    )
    response = messaging.send_each_for_multicast(message, app=_firebase_app())
    for token, item in zip(tokens, response.responses):
        if item.success:
            continue
        error = item.exception
        if isinstance(error, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
            result.invalid.append(token)
        elif isinstance(error, (exceptions.UnavailableError, exceptions.InternalError, messaging.QuotaExceededError)):
            result.retry.append(token)
        else:
            logger.warning("Push to one device failed and will not be retried: %s", type(error).__name__)
    return result
