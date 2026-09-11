"""Model-shape tests for `User.is_verified` and `EmailToken` (design.md DD1/DD2).

Only shape/default assertions live here — hashing/expiry/throttle *behavior*
is covered by `tokens.py`'s hypothesis test and `services.py`'s RED tests,
per design.md's Testing Strategy.
"""
import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.users.models import EmailToken, User
from apps.users.tests.factories import make_user


@pytest.mark.django_db
def test_new_user_defaults_to_unverified():
    user = make_user(email="fresh@example.com")

    assert user.is_verified is False


@pytest.mark.django_db
def test_email_token_can_be_created_with_required_fields():
    user = make_user(email="owner@example.com")
    now = timezone.now()

    token = EmailToken.objects.create(
        user=user,
        purpose="verify",
        token_hash="a" * 64,
        expires_at=now + timedelta(hours=24),
    )

    assert isinstance(token.id, uuid.UUID)
    assert token.user_id == user.id
    assert token.purpose == "verify"
    assert token.used_at is None
    assert token.created_at is not None


@pytest.mark.django_db
def test_email_token_hash_is_unique():
    user = make_user(email="dup@example.com")
    now = timezone.now()
    EmailToken.objects.create(
        user=user, purpose="verify", token_hash="b" * 64, expires_at=now + timedelta(hours=24)
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        EmailToken.objects.create(
            user=user, purpose="reset", token_hash="b" * 64, expires_at=now + timedelta(hours=1)
        )
