"""Plain builder functions for the users domain tests.

No `factory_boy` — matches Cycle 1's precedent (`apps/uml_modeling/tests/factories.py`),
so no new dependency is introduced. These builders construct rows directly
through the ORM.
"""
import itertools

from apps.users.models import User

_counter = itertools.count(1)


def _unique_suffix() -> int:
    return next(_counter)


def make_user(*, email: str | None = None, password: str = "a-strong-pass-0", full_name: str = "") -> User:
    email = email or f"user{_unique_suffix()}@example.com"
    return User.objects.create_user(email=email, password=password, full_name=full_name)
