"""Transactions that survive concurrent writers on MongoDB.

PostgreSQL serialised writers with `SELECT ... FOR UPDATE`: the second one
waited for the first. MongoDB has no row locks. Inside a transaction it lets
both run and aborts the one that writes a document the other already changed
(error 112, labelled `TransientTransactionError`), expecting the caller to run
the transaction again. `atomic_retrying` does exactly that, so a function that
reads a row and then rewrites it still behaves as if it ran alone.

The rule that makes it correct: the transactional function must WRITE the row
it decided from (a revision bump, a status change). A function that only reads
a row and writes something else would not conflict; use `touch` on the row
that guards the decision.
"""

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import TypeVar

from django.db import DatabaseError, connection
from django.utils import timezone
from django_mongodb_backend import transaction

T = TypeVar("T")

DEFAULT_ATTEMPTS = 8


def is_write_conflict(exc: BaseException) -> bool:
    """True when MongoDB aborted the transaction because another one won."""
    cause = exc.__cause__ or exc.__context__
    has_label = getattr(cause, "has_error_label", None)
    return bool(has_label and has_label("TransientTransactionError"))


def run_atomic(
    body: Callable[[], T],
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    also_retry: tuple[type[DatabaseError], ...] = (),
) -> T:
    """Run `body` in a transaction, running it again if it loses a conflict.

    `also_retry` names extra errors worth a fresh attempt, for a body that
    computes a value another writer may have taken (the next version number):
    the retry recomputes it from the winner's data.

    Called inside an outer transaction it just runs `body`: only the outermost
    block can restart cleanly, and it is the one that retries.
    """
    if connection.in_atomic_block_mongo:
        return body()
    for attempt in range(1, attempts + 1):
        try:
            with transaction.atomic():
                return body()
        except DatabaseError as exc:
            retryable = is_write_conflict(exc) or isinstance(exc, also_retry)
            if attempt == attempts or not retryable:
                raise
            # Random pause that grows with each attempt (capped), so the
            # competing writers do not collide again and a slow winner has
            # time to commit: about 3 seconds in total before giving up.
            time.sleep(random.uniform(0, min(0.05 * 2**attempt, 0.5)))
    raise AssertionError("unreachable")  # pragma: no cover


def atomic_retrying(
    func: Callable[..., T] | None = None,
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    also_retry: tuple[type[DatabaseError], ...] = (),
):
    """Decorator form of `run_atomic` (usable bare or with `attempts=`)."""

    def decorate(inner: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(inner)
        def wrapper(*args, **kwargs) -> T:
            return run_atomic(lambda: inner(*args, **kwargs), attempts=attempts, also_retry=also_retry)

        return wrapper

    return decorate(func) if func is not None else decorate


def touch(instance, field: str = "updated_at") -> None:
    """Rewrite `instance`'s timestamp so concurrent transactions that touched
    the same row conflict. This is the stand-in for `select_for_update()` when
    a decision is guarded by a row (a quota, a last-owner rule) that the
    function would not otherwise rewrite. The value must really change: a
    write that changes nothing does not conflict."""
    type(instance)._base_manager.filter(pk=instance.pk).update(**{field: timezone.now()})
