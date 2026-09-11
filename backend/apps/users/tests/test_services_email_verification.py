"""RED-first tests for `verify_email` and the `register_user` on-commit
verification-email wiring (email-verification spec; design.md Testing
Strategy § "on_commit timing").

`django_capture_on_commit_callbacks(execute=True)` is required here: a plain
`pytest.mark.django_db` test never commits its transaction, so an
`on_commit`-scheduled callback silently never fires and a naive assertion
would pass vacuously even if the wiring were broken.
"""
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.organizations.errors import OrganizationError
from apps.users import services
from apps.users.errors import TokenExpiredError, TokenInvalidError, TokenUsedError
from apps.users.models import EmailToken
from apps.users.tests.factories import make_user
from apps.users.tokens import issue_token


@pytest.mark.django_db
class TestRegisterUserSchedulesVerificationEmail:
    def test_commit_creates_one_token_and_sends_one_email(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            user = services.register_user(
                email="verify-me@example.com", password="a-very-strong-pass-1"
            )

        tokens = EmailToken.objects.filter(user=user, purpose="verify")
        assert tokens.count() == 1
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["verify-me@example.com"]

    def test_no_email_is_sent_before_commit_within_the_capture_block(
        self, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks() as callbacks:
            user = services.register_user(
                email="deferred@example.com", password="a-very-strong-pass-1"
            )
            # Not executed yet: the callback is only captured, not run.
            assert len(mail.outbox) == 0

        assert len(callbacks) == 1

    def test_rolled_back_registration_creates_no_token_and_sends_no_email(
        self, django_capture_on_commit_callbacks, monkeypatch
    ):
        def _raise_organization_error(*, source):
            raise OrganizationError("Could not generate a unique organization slug.")

        monkeypatch.setattr(services, "generate_unique_slug", _raise_organization_error)

        with pytest.raises(OrganizationError):
            with django_capture_on_commit_callbacks(execute=True):
                services.register_user(email="rollback2@example.com", password="a-very-strong-pass-1")

        assert EmailToken.objects.count() == 0
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestVerifyEmail:
    def test_valid_token_marks_user_verified_and_token_used(self):
        user = make_user(email="tobeverified@example.com")
        raw, token = issue_token(user, "verify")

        result = services.verify_email(token=raw)

        user.refresh_from_db()
        token.refresh_from_db()
        assert result.pk == user.pk
        assert user.is_verified is True
        assert token.used_at is not None

    def test_already_used_token_is_rejected(self):
        user = make_user(email="usedtoken@example.com")
        raw, token = issue_token(user, "verify")
        services.verify_email(token=raw)

        with pytest.raises(TokenUsedError):
            services.verify_email(token=raw)

        user.refresh_from_db()
        assert user.is_verified is True  # unchanged by the second (rejected) call

    def test_expired_token_is_rejected(self):
        user = make_user(email="expiredtoken@example.com")
        raw, token = issue_token(user, "verify")
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=["expires_at"])

        with pytest.raises(TokenExpiredError):
            services.verify_email(token=raw)

    def test_invalid_unknown_token_is_rejected(self):
        with pytest.raises(TokenInvalidError):
            services.verify_email(token="not-a-real-token")
