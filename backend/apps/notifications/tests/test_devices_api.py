"""Device registration for push notifications (GitHub #19)."""
import json

import pytest
from django.test import Client

from apps.notifications.models import DeviceToken
from apps.users.mobile_tokens import issue_mobile_token
from apps.users.tests.factories import make_user


def _bearer(user) -> dict:
    raw, _ = issue_mobile_token(user, device_name="phone")
    return {"HTTP_AUTHORIZATION": f"Bearer {raw}"}


def _register(client, user, token="fcm-token-1", platform="android"):
    return client.post(
        "/api/devices",
        data=json.dumps({"token": token, "platform": platform}),
        content_type="application/json",
        **_bearer(user),
    )


@pytest.fixture
def client() -> Client:
    # No CSRF cookie: a bearer token is what authorizes the call.
    return Client(enforce_csrf_checks=True)


@pytest.mark.django_db
class TestRegisterDevice:
    def test_a_logged_in_user_registers_a_device_token(self, client):
        user = make_user()

        response = _register(client, user)

        assert response.status_code == 204
        assert list(DeviceToken.objects.values_list("token", "platform")) == [("fcm-token-1", "android")]
        assert DeviceToken.objects.get().user_id == user.id

    def test_registering_the_same_token_twice_keeps_a_single_row(self, client):
        user = make_user()

        _register(client, user)
        _register(client, user)

        assert DeviceToken.objects.count() == 1

    def test_a_token_follows_whoever_logged_in_on_that_phone_last(self, client):
        first, second = make_user(), make_user()
        _register(client, first, token="shared-phone")

        _register(client, second, token="shared-phone")

        assert DeviceToken.objects.get(token="shared-phone").user_id == second.id

    def test_it_needs_authentication(self, client):
        response = client.post(
            "/api/devices",
            data=json.dumps({"token": "x", "platform": "android"}),
            content_type="application/json",
        )

        assert response.status_code in (401, 403)
        assert DeviceToken.objects.count() == 0

    @pytest.mark.parametrize("token", ["", "   "])
    def test_an_empty_token_is_rejected(self, client, token):
        assert _register(client, make_user(), token=token).status_code == 422


@pytest.mark.django_db
class TestUnregisterDevice:
    def _delete(self, client, user, token):
        return client.delete(
            "/api/devices",
            data=json.dumps({"token": token}),
            content_type="application/json",
            **_bearer(user),
        )

    def test_a_user_removes_their_own_token(self, client):
        user = make_user()
        _register(client, user)

        assert self._delete(client, user, "fcm-token-1").status_code == 204
        assert DeviceToken.objects.count() == 0

    def test_a_user_cannot_remove_someone_elses_token(self, client):
        owner, other = make_user(), make_user()
        _register(client, owner)

        self._delete(client, other, "fcm-token-1")

        assert DeviceToken.objects.count() == 1

    def test_removing_an_unknown_token_is_not_an_error(self, client):
        assert self._delete(client, make_user(), "nope").status_code == 204
