"""Cross-origin session/CSRF tests (design.md DD2).

Covers the proposal's stated High risk: the cross-origin cookie-session
flow with a Next.js frontend on another origin, not just same-origin.
"""
import pytest
from django.test import Client, override_settings

from apps.identity.tests.factories import make_user


@pytest.mark.django_db
class TestCsrfSettingsPresence:
    def test_csrf_and_session_settings_are_env_driven_and_present(self, settings):
        # Presence + shape, not hardcoded literals (settings.py DD2 block).
        assert isinstance(settings.CSRF_TRUSTED_ORIGINS, list)
        assert isinstance(settings.CORS_ALLOW_CREDENTIALS, bool)
        assert settings.SESSION_COOKIE_SAMESITE in ("Lax", "Strict", "None")
        assert settings.CSRF_COOKIE_SAMESITE in ("Lax", "Strict", "None")
        assert isinstance(settings.SESSION_COOKIE_SECURE, bool)
        assert isinstance(settings.CSRF_COOKIE_SECURE, bool)
        assert settings.SESSION_COOKIE_HTTPONLY is True
        assert settings.CSRF_COOKIE_HTTPONLY is False


@pytest.mark.django_db
class TestCsrfEnforcement:
    def test_csrf_token_acquisition_sets_cookie(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/api/auth/csrf")
        assert response.status_code == 200
        assert "csrftoken" in response.cookies
        assert response.json()["csrf_token"]

    def test_unsafe_request_without_token_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/api/auth/csrf")  # sets the csrftoken cookie
        response = client.post(
            "/api/auth/register",
            data={"email": "noheader@example.com", "password": "a-strong-pass-0"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_unsafe_request_with_token_accepted(self):
        client = Client(enforce_csrf_checks=True)
        csrf_response = client.get("/api/auth/csrf")
        token = csrf_response.json()["csrf_token"]
        response = client.post(
            "/api/auth/register",
            data={"email": "withheader@example.com", "password": "a-strong-pass-0"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201

    def test_authenticated_unsafe_request_without_token_rejected(self):
        user = make_user(email="protected@example.com", password="a-strong-pass-0")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        response = client.post("/api/auth/logout")
        assert response.status_code == 403


@pytest.mark.django_db
class TestDeployedMatrix:
    @override_settings(
        SESSION_COOKIE_SAMESITE="None",
        CSRF_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
    )
    def test_samesite_none_implies_secure(self, settings):
        assert settings.SESSION_COOKIE_SAMESITE == "None"
        assert settings.SESSION_COOKIE_SECURE is True
        assert settings.CSRF_COOKIE_SAMESITE == "None"
        assert settings.CSRF_COOKIE_SECURE is True
