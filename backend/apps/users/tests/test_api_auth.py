"""Integration tests for `/api/auth/*` (design.md API Surface table).

Uses Django's test `Client` against the mounted Ninja routes — real HTTP,
real session/CSRF machinery, no mocking.
"""
import pytest

from apps.users.tests.factories import make_user


@pytest.mark.django_db
class TestCsrf:
    def test_csrf_endpoint_returns_token_and_sets_cookie(self, auth_client):
        response = auth_client.get("/api/auth/csrf")
        assert response.status_code == 200
        body = response.json()
        assert "csrf_token" in body and body["csrf_token"]
        assert "csrftoken" in response.cookies


@pytest.mark.django_db
class TestRegister:
    def test_successful_registration_creates_user_and_session(self, auth_client):
        response = auth_client.post(
            "/api/auth/register",
            data={"email": "newuser@example.com", "password": "a-strong-pass-0", "full_name": "New User"},
            content_type="application/json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "newuser@example.com"
        assert "_auth_user_id" in auth_client.session

    def test_duplicate_email_rejected(self, auth_client):
        make_user(email="dupe@example.com")
        response = auth_client.post(
            "/api/auth/register",
            data={"email": "dupe@example.com", "password": "a-strong-pass-0"},
            content_type="application/json",
        )
        assert response.status_code == 409
        assert response.json()["code"] == "duplicate_email"

    def test_weak_password_rejected(self, auth_client):
        response = auth_client.post(
            "/api/auth/register",
            data={"email": "weak@example.com", "password": "12345678"},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json()["code"] == "password_invalid"


@pytest.mark.django_db
class TestLogin:
    def test_successful_login_establishes_session(self, auth_client):
        make_user(email="loginme@example.com", password="a-strong-pass-0")
        response = auth_client.post(
            "/api/auth/login",
            data={"email": "loginme@example.com", "password": "a-strong-pass-0"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["email"] == "loginme@example.com"
        assert "_auth_user_id" in auth_client.session

    def test_invalid_credentials_rejected(self, auth_client):
        make_user(email="realuser@example.com", password="a-strong-pass-0")
        response = auth_client.post(
            "/api/auth/login",
            data={"email": "realuser@example.com", "password": "wrong-password"},
            content_type="application/json",
        )
        assert response.status_code == 401
        assert response.json()["code"] == "invalid_credentials"

    def test_unknown_email_rejected_with_same_generic_error(self, auth_client):
        response = auth_client.post(
            "/api/auth/login",
            data={"email": "nobody@example.com", "password": "whatever-0"},
            content_type="application/json",
        )
        assert response.status_code == 401
        assert response.json()["code"] == "invalid_credentials"


@pytest.mark.django_db
class TestLogoutAndMe:
    def test_me_requires_authentication(self, auth_client):
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_returns_authenticated_identity(self, auth_client):
        user = make_user(email="me@example.com", password="a-strong-pass-0")
        auth_client.force_login(user)
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "me@example.com"

    def test_logout_invalidates_session(self, auth_client):
        user = make_user(email="bye@example.com", password="a-strong-pass-0")
        auth_client.force_login(user)
        response = auth_client.post("/api/auth/logout")
        assert response.status_code == 204

        follow_up = auth_client.get("/api/auth/me")
        assert follow_up.status_code == 401
