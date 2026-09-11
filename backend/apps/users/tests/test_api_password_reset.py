"""Integration tests for `/api/auth/password-reset/{request,confirm}`
(design.md API Surface table; password-reset spec § "Anti-Enumeration
Reset Request").
"""
import pytest
from django.test import Client

from apps.users.tests.factories import make_user
from apps.users.tokens import issue_token


@pytest.mark.django_db
class TestRequestPasswordResetEndpoint:
    def test_existing_and_nonexistent_email_return_byte_identical_responses(self, auth_client):
        make_user(email="existsapi@example.com", password="a-strong-pass-0")

        existing_response = auth_client.post(
            "/api/auth/password-reset/request",
            data={"email": "existsapi@example.com"},
            content_type="application/json",
        )
        missing_response = auth_client.post(
            "/api/auth/password-reset/request",
            data={"email": "ghostapi@example.com"},
            content_type="application/json",
        )

        assert existing_response.status_code == missing_response.status_code == 200
        assert existing_response.content == missing_response.content

    def test_throttled_response_is_also_byte_identical(self, auth_client):
        make_user(email="throttledapi@example.com", password="a-strong-pass-0")
        auth_client.post(
            "/api/auth/password-reset/request",
            data={"email": "throttledapi@example.com"},
            content_type="application/json",
        )

        throttled_response = auth_client.post(
            "/api/auth/password-reset/request",
            data={"email": "throttledapi@example.com"},
            content_type="application/json",
        )
        missing_response = auth_client.post(
            "/api/auth/password-reset/request",
            data={"email": "stillghost@example.com"},
            content_type="application/json",
        )

        assert throttled_response.status_code == missing_response.status_code == 200
        assert throttled_response.content == missing_response.content

    def test_csrf_enforced_on_anonymous_endpoint(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/api/auth/csrf")
        response = client.post(
            "/api/auth/password-reset/request",
            data={"email": "csrftest@example.com"},
            content_type="application/json",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestConfirmPasswordResetEndpoint:
    def test_valid_token_returns_200(self, auth_client):
        user = make_user(email="confirmapi@example.com")
        raw, _token = issue_token(user, "reset")

        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            data={"token": raw, "password": "brand-new-strong-1"},
            content_type="application/json",
        )
        assert response.status_code == 200

    def test_weak_password_returns_400(self, auth_client):
        user = make_user(email="weakconfirmapi@example.com")
        raw, _token = issue_token(user, "reset")

        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            data={"token": raw, "password": "123"},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json()["code"] == "password_invalid"

    def test_expired_token_returns_400(self, auth_client):
        from django.utils import timezone
        from datetime import timedelta

        user = make_user(email="expiredconfirmapi@example.com")
        raw, token = issue_token(user, "reset")
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=["expires_at"])

        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            data={"token": raw, "password": "brand-new-strong-1"},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json()["code"] == "token_expired"

    def test_used_token_returns_409(self, auth_client):
        user = make_user(email="usedconfirmapi@example.com")
        raw, _token = issue_token(user, "reset")
        auth_client.post(
            "/api/auth/password-reset/confirm",
            data={"token": raw, "password": "brand-new-strong-1"},
            content_type="application/json",
        )

        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            data={"token": raw, "password": "another-brand-new-2"},
            content_type="application/json",
        )
        assert response.status_code == 409
        assert response.json()["code"] == "token_used"

    def test_invalid_token_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            data={"token": "garbage", "password": "brand-new-strong-1"},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json()["code"] == "token_invalid"

    def test_csrf_enforced_on_anonymous_endpoint(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/api/auth/csrf")
        response = client.post(
            "/api/auth/password-reset/confirm",
            data={"token": "whatever", "password": "irrelevant-1"},
            content_type="application/json",
        )
        assert response.status_code == 403
