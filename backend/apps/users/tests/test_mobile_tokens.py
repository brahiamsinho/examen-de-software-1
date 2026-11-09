"""Service-level tests for the mobile bearer token (issue #19, S6)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.users.mobile_tokens import issue_mobile_token, resolve_mobile_token, revoke_mobile_token
from apps.users.models import MobileToken
from apps.users.tests.factories import make_user


@pytest.mark.django_db
class TestIssue:
    def test_only_the_hash_is_stored_never_the_raw_token(self):
        user = make_user()

        raw, token = issue_mobile_token(user, device_name="Pixel")

        assert len(raw) >= 40
        stored = MobileToken.objects.get(pk=token.pk)
        assert raw not in {stored.token_hash, stored.device_name}
        assert len(stored.token_hash) == 64 and stored.token_hash != raw
        assert stored.device_name == "Pixel"

    def test_each_token_is_different_and_expires_in_the_future(self):
        user = make_user()

        first, a = issue_mobile_token(user)
        second, b = issue_mobile_token(user)

        assert first != second
        assert a.expires_at > timezone.now() + timedelta(days=29)


@pytest.mark.django_db
class TestResolve:
    def test_a_valid_token_resolves_to_its_user(self):
        user = make_user()
        raw, _ = issue_mobile_token(user)

        assert resolve_mobile_token(raw) == user

    @pytest.mark.parametrize("candidate", ["", "nope", "a" * 43])
    def test_an_unknown_token_resolves_to_nobody(self, candidate):
        assert resolve_mobile_token(candidate) is None

    def test_an_expired_token_resolves_to_nobody(self):
        raw, token = issue_mobile_token(make_user())
        MobileToken.objects.filter(pk=token.pk).update(expires_at=timezone.now() - timedelta(seconds=1))

        assert resolve_mobile_token(raw) is None

    def test_a_revoked_token_resolves_to_nobody(self):
        raw, _ = issue_mobile_token(make_user())

        assert revoke_mobile_token(raw) is True

        assert resolve_mobile_token(raw) is None

    def test_a_deactivated_user_loses_the_token(self):
        user = make_user()
        raw, _ = issue_mobile_token(user)
        user.is_active = False
        user.save(update_fields=["is_active"])

        assert resolve_mobile_token(raw) is None

    def test_revoking_one_token_leaves_the_users_other_tokens_alive(self):
        user = make_user()
        first, _ = issue_mobile_token(user, device_name="phone")
        second, _ = issue_mobile_token(user, device_name="tablet")

        revoke_mobile_token(first)

        assert resolve_mobile_token(first) is None
        assert resolve_mobile_token(second) == user

    def test_revoking_an_unknown_token_reports_false(self):
        assert revoke_mobile_token("nope") is False

    def test_resolving_records_the_last_use(self):
        raw, token = issue_mobile_token(make_user())
        assert token.last_used_at is None

        resolve_mobile_token(raw)

        assert MobileToken.objects.get(pk=token.pk).last_used_at is not None
