"""RED-first tests for `request_password_reset` / `confirm_password_reset`
(password-reset spec; design.md DD4, Testing Strategy § "Enumeration
parity" / "Single-use + sibling invalidation").

`request_password_reset` never raises and never branches visibly — service
tests assert side effects (token/email/delay), not return value shape.
Byte-identical response parity at the HTTP layer is covered by the API
tests (`test_api_auth.py`).
"""
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.users import services
from apps.users.errors import PasswordPolicyError, TokenExpiredError, TokenInvalidError, TokenUsedError
from apps.users.models import EmailToken
from apps.users.tests.factories import make_user
from apps.users.tokens import issue_token


@pytest.mark.django_db
class TestRequestPasswordReset:
    def test_existing_account_creates_token_and_sends_email_no_artificial_delay(
        self, django_capture_on_commit_callbacks, monkeypatch
    ):
        user = make_user(email="reset-me@example.com")
        sleep_calls: list[float] = []
        monkeypatch.setattr(services.time, "sleep", lambda seconds: sleep_calls.append(seconds))

        with django_capture_on_commit_callbacks(execute=True):
            result = services.request_password_reset(email="reset-me@example.com")

        assert result is None
        assert EmailToken.objects.filter(user=user, purpose="reset").count() == 1
        assert len(mail.outbox) == 1
        assert sleep_calls == []

    def test_nonexistent_account_creates_nothing_and_applies_fixed_delay(self, monkeypatch):
        sleep_calls: list[float] = []
        monkeypatch.setattr(services.time, "sleep", lambda seconds: sleep_calls.append(seconds))

        result = services.request_password_reset(email="ghost@example.com")

        assert result is None
        assert EmailToken.objects.count() == 0
        assert len(mail.outbox) == 0
        assert sleep_calls == [services._RESET_ANTI_ENUMERATION_DELAY_SECONDS]

    def test_throttled_existing_account_creates_no_new_token_and_applies_fixed_delay(
        self, monkeypatch
    ):
        user = make_user(email="throttled@example.com")
        issue_token(user, "reset")  # outstanding, recent -> subject to cooldown
        sleep_calls: list[float] = []
        monkeypatch.setattr(services.time, "sleep", lambda seconds: sleep_calls.append(seconds))

        result = services.request_password_reset(email="throttled@example.com")

        assert result is None
        assert EmailToken.objects.filter(user=user, purpose="reset").count() == 1
        assert len(mail.outbox) == 0
        assert sleep_calls == [services._RESET_ANTI_ENUMERATION_DELAY_SECONDS]

    def test_reset_token_expiry_is_exactly_one_hour(self, django_capture_on_commit_callbacks):
        user = make_user(email="onehour@example.com")

        with django_capture_on_commit_callbacks(execute=True):
            services.request_password_reset(email="onehour@example.com")

        token = EmailToken.objects.get(user=user, purpose="reset")
        delta = token.expires_at - token.created_at
        assert timedelta(minutes=59) < delta <= timedelta(hours=1, seconds=1)


@pytest.mark.django_db
class TestConfirmPasswordReset:
    def test_successful_reset_changes_password_and_verifies_user(self):
        user = make_user(email="confirmme@example.com", password="old-strong-pass-1")
        raw, _token = issue_token(user, "reset")

        result = services.confirm_password_reset(token=raw, new_password="new-strong-pass-2")

        user.refresh_from_db()
        assert result.pk == user.pk
        assert user.check_password("new-strong-pass-2")
        assert user.is_verified is True

    def test_successful_reset_invalidates_other_outstanding_reset_tokens(self):
        user = make_user(email="siblings@example.com", password="old-strong-pass-1")
        raw_a, _token_a = issue_token(user, "reset")
        raw_b, _token_b = issue_token(user, "reset")

        services.confirm_password_reset(token=raw_a, new_password="new-strong-pass-2")

        with pytest.raises((TokenUsedError, TokenInvalidError)):
            services.confirm_password_reset(token=raw_b, new_password="another-strong-pass-3")

    def test_weak_password_rejected_token_remains_unused(self):
        user = make_user(email="weakreset@example.com", password="old-strong-pass-1")
        raw, token = issue_token(user, "reset")

        with pytest.raises(PasswordPolicyError):
            services.confirm_password_reset(token=raw, new_password="123")

        token.refresh_from_db()
        user.refresh_from_db()
        assert token.used_at is None
        assert user.check_password("old-strong-pass-1")

    def test_expired_token_rejected(self):
        user = make_user(email="expiredreset@example.com")
        raw, token = issue_token(user, "reset")
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=["expires_at"])

        with pytest.raises(TokenExpiredError):
            services.confirm_password_reset(token=raw, new_password="new-strong-pass-2")

    def test_already_used_token_rejected(self):
        user = make_user(email="usedreset@example.com")
        raw, _token = issue_token(user, "reset")
        services.confirm_password_reset(token=raw, new_password="new-strong-pass-2")

        with pytest.raises(TokenUsedError):
            services.confirm_password_reset(token=raw, new_password="another-strong-pass-3")

    def test_invalid_unknown_token_rejected(self):
        with pytest.raises(TokenInvalidError):
            services.confirm_password_reset(token="not-a-real-token", new_password="new-strong-pass-2")
