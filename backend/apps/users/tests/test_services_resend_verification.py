"""RED-first tests for `resend_verification` (email-verification spec §
"Resend Verification with Cooldown and Hourly Cap"; design.md DD3, Testing
Strategy § "Throttle arithmetic" — explicit `created_at`, no freezegun).
"""
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.users import services
from apps.users.errors import ResendCooldownError, ResendRateLimitError
from apps.users.models import EmailToken
from apps.users.tests.factories import make_user


def _backdated_token(user, *, seconds_ago: int) -> EmailToken:
    token = EmailToken.objects.create(
        user=user,
        purpose="verify",
        token_hash=f"hash-{seconds_ago}-{user.pk}",
        expires_at=timezone.now() + timedelta(hours=24),
    )
    token.created_at = timezone.now() - timedelta(seconds=seconds_ago)
    token.save(update_fields=["created_at"])
    return token


@pytest.mark.django_db
class TestResendVerification:
    def test_resend_within_59_seconds_is_rejected(self, django_capture_on_commit_callbacks):
        user = make_user(email="cooldown@example.com")
        _backdated_token(user, seconds_ago=59)

        with pytest.raises(ResendCooldownError):
            with django_capture_on_commit_callbacks(execute=True):
                services.resend_verification(user=user)

        assert EmailToken.objects.filter(user=user).count() == 1
        assert len(mail.outbox) == 0

    def test_resend_after_61_seconds_is_accepted(self, django_capture_on_commit_callbacks):
        user = make_user(email="afterccooldown@example.com")
        _backdated_token(user, seconds_ago=61)

        with django_capture_on_commit_callbacks(execute=True):
            services.resend_verification(user=user)

        assert EmailToken.objects.filter(user=user).count() == 2
        assert len(mail.outbox) == 1

    def test_5th_token_in_rolling_hour_is_accepted_6th_is_capped(
        self, django_capture_on_commit_callbacks
    ):
        user = make_user(email="cap@example.com")
        # 4 tokens already exist, oldest > 60s ago so cooldown doesn't block.
        for i in range(4):
            _backdated_token(user, seconds_ago=120 + i)

        with django_capture_on_commit_callbacks(execute=True):
            services.resend_verification(user=user)  # 5th: ok

        assert EmailToken.objects.filter(user=user).count() == 5

        # Push the newest token's created_at back past cooldown so only the
        # rolling-hour cap (not the cooldown) is under test for the 6th call.
        newest = EmailToken.objects.filter(user=user).order_by("-created_at").first()
        newest.created_at = timezone.now() - timedelta(seconds=120)
        newest.save(update_fields=["created_at"])

        with pytest.raises(ResendRateLimitError):
            services.resend_verification(user=user)

        assert EmailToken.objects.filter(user=user).count() == 5
