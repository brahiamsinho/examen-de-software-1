"""Integration tests for `/api/auth/verify-email` and
`/api/auth/resend-verification` (design.md API Surface table).
"""
import pytest
from django.test import Client

from apps.users.tests.factories import make_user
from apps.users.tokens import issue_token


@pytest.mark.django_db
class TestVerifyEmailEndpoint:
    def test_valid_token_returns_200(self, auth_client):
        user = make_user(email="verifyapi@example.com")
        raw, _token = issue_token(user, "verify")

        response = auth_client.post(
            "/api/auth/verify-email", data={"token": raw}, content_type="application/json"
        )
        assert response.status_code == 200

    def test_invalid_token_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/auth/verify-email", data={"token": "garbage"}, content_type="application/json"
        )
        assert response.status_code == 400
        assert response.json()["code"] == "token_invalid"

    def test_used_token_returns_409(self, auth_client):
        user = make_user(email="usedapi@example.com")
        raw, _token = issue_token(user, "verify")
        auth_client.post("/api/auth/verify-email", data={"token": raw}, content_type="application/json")

        response = auth_client.post(
            "/api/auth/verify-email", data={"token": raw}, content_type="application/json"
        )
        assert response.status_code == 409
        assert response.json()["code"] == "token_used"

    def test_csrf_enforced_on_anonymous_endpoint(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/api/auth/csrf")
        response = client.post(
            "/api/auth/verify-email", data={"token": "whatever"}, content_type="application/json"
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestResendVerificationEndpoint:
    def test_requires_authentication(self, auth_client):
        response = auth_client.post("/api/auth/resend-verification")
        assert response.status_code == 401

    def test_authenticated_resend_returns_202(self, auth_client):
        user = make_user(email="resendapi@example.com", password="a-strong-pass-0")
        auth_client.force_login(user)

        response = auth_client.post("/api/auth/resend-verification")
        assert response.status_code == 202

    def test_cooldown_returns_429(self, auth_client):
        user = make_user(email="cooldownapi@example.com", password="a-strong-pass-0")
        auth_client.force_login(user)
        auth_client.post("/api/auth/resend-verification")

        response = auth_client.post("/api/auth/resend-verification")
        assert response.status_code == 429
        assert response.json()["code"] == "resend_cooldown"

    def test_csrf_enforced_on_authenticated_endpoint(self):
        user = make_user(email="resendcsrf@example.com", password="a-strong-pass-0")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        response = client.post("/api/auth/resend-verification")
        assert response.status_code == 403
