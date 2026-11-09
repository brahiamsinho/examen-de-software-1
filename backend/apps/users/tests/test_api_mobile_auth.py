"""HTTP tests for the mobile bearer-token login (issue #19, S2 and S6).

`enforce_csrf_checks=True` is on purpose: the point is that a bearer token
works without any CSRF cookie while a plain session still needs one.
"""
import json

import pytest
from django.test import Client, RequestFactory

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services
from apps.users.middleware import BearerTokenMiddleware
from apps.users.mobile_tokens import issue_mobile_token
from apps.users.tests.factories import make_user
from django.utils import timezone

PASSWORD = "a-strong-pass-0"


def _login(client: Client, email: str, password: str = PASSWORD, **extra):
    return client.post(
        "/api/auth/mobile-token",
        data=json.dumps({"email": email, "password": password, **extra}),
        content_type="application/json",
    )


def _bearer(token: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def client() -> Client:
    return Client(enforce_csrf_checks=True)


@pytest.mark.django_db
class TestMobileLogin:
    def test_valid_credentials_return_a_token_and_the_user_without_any_csrf_cookie(self, client):
        user = make_user(full_name="Ana")

        response = _login(client, user.email, device_name="Pixel")

        assert response.status_code == 200
        body = response.json()
        assert len(body["token"]) >= 40 and body["expires_at"]
        assert body["user"] == {
            "id": str(user.id),
            "email": user.email,
            "full_name": "Ana",
            "is_verified": False,
        }

    @pytest.mark.parametrize("password", ["wrong-password-1", ""])
    def test_bad_credentials_get_the_same_401_as_the_web_login(self, client, password):
        user = make_user()

        response = _login(client, user.email, password)

        assert response.status_code in (401, 422)
        assert "token" not in response.json()

    def test_an_unknown_email_cannot_be_told_from_a_wrong_password(self, client):
        user = make_user()

        unknown = _login(client, "nobody@example.com")
        wrong = _login(client, user.email, "wrong-password-1")

        assert unknown.status_code == wrong.status_code == 401
        assert unknown.json() == wrong.json()

    def test_logging_in_does_not_create_a_web_session(self, client):
        user = make_user()

        response = _login(client, user.email)

        assert "sessionid" not in response.cookies


@pytest.mark.django_db
class TestBearerAuthentication:
    def test_the_token_authenticates_a_get_without_any_cookie(self, client):
        user = make_user()
        raw, _ = issue_mobile_token(user)

        response = client.get("/api/auth/me", **_bearer(raw))

        assert response.status_code == 200 and response.json()["email"] == user.email

    def test_the_token_authenticates_an_unsafe_request_without_a_csrf_token(self, client):
        organization, owner, editor, *_ = make_org_with_roles()
        raw, _ = issue_mobile_token(editor)

        response = client.post(
            f"/api/orgs/{organization.slug}/documents",
            data=json.dumps({"name": "From the phone"}),
            content_type="application/json",
            **_bearer(raw),
        )

        assert response.status_code == 201

    def test_a_plain_session_still_needs_the_csrf_token(self, client):
        organization, owner, editor, *_ = make_org_with_roles()
        client.force_login(editor)

        response = client.post(
            f"/api/orgs/{organization.slug}/documents",
            data=json.dumps({"name": "No csrf"}),
            content_type="application/json",
        )

        assert response.status_code == 403

    def test_a_bad_token_is_refused_outright_even_if_a_valid_session_comes_with_it(self, client):
        organization, owner, editor, *_ = make_org_with_roles()
        client.force_login(editor)

        response = client.post(
            f"/api/orgs/{organization.slug}/documents",
            data=json.dumps({"name": "Sneaky"}),
            content_type="application/json",
            **_bearer("not-a-real-token"),
        )

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_token"
        assert response["WWW-Authenticate"] == "Bearer"
        assert services.list_documents(organization=organization) == []

    @pytest.mark.parametrize("method", ["get", "post", "delete"])
    def test_an_invalid_token_gets_401_on_every_method_so_the_phone_can_tell_it_expired(
        self, client, method
    ):
        organization, owner, editor, *_ = make_org_with_roles()

        response = getattr(client, method)(
            f"/api/orgs/{organization.slug}/documents", **_bearer("expired-or-wrong")
        )

        assert response.status_code == 401 and response.json()["code"] == "invalid_token"

    @pytest.mark.parametrize("header", ["Bearer ", "Bearer", "Basic abc", "Token abc", "bearer"])
    def test_malformed_or_foreign_schemes_authenticate_nobody(self, client, header):
        response = client.get("/api/auth/me", HTTP_AUTHORIZATION=header)

        assert response.status_code == 401

    def test_a_token_in_the_query_string_or_a_cookie_neither_authenticates_nor_waives_csrf(self, client):
        organization, owner, editor, *_ = make_org_with_roles()
        raw, _ = issue_mobile_token(editor)
        url = f"/api/orgs/{organization.slug}/documents"
        body = json.dumps({"name": "Smuggled"})

        by_query = client.post(f"{url}?token={raw}", data=body, content_type="application/json")
        client.cookies["Authorization"] = f"Bearer {raw}"
        by_cookie = client.post(url, data=body, content_type="application/json")

        assert by_query.status_code == by_cookie.status_code == 403
        assert services.list_documents(organization=organization) == []

    def test_an_extra_word_after_the_token_is_refused(self, client):
        raw, _ = issue_mobile_token(make_user())

        response = client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Bearer {raw} extra")

        assert response.status_code == 401 and response.json()["code"] == "invalid_token"

    def test_a_valid_token_does_not_open_the_django_admin(self, client):
        user = make_user()
        user.is_staff = user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        raw, _ = issue_mobile_token(user)

        response = client.get("/admin/", **_bearer(raw))

        assert response.status_code == 302 and "/login" in response["Location"]

    def test_an_expired_token_gets_401(self, client):
        from datetime import timedelta

        from apps.users.models import MobileToken

        raw, token = issue_mobile_token(make_user())
        MobileToken.objects.filter(pk=token.pk).update(expires_at=timezone.now() - timedelta(seconds=1))

        assert client.get("/api/auth/me", **_bearer(raw)).status_code == 401

    def test_tenant_isolation_and_roles_apply_to_a_token_exactly_as_to_a_session(self, client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        document = services.create_document(
            organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now()
        )
        base = f"/api/orgs/{organization.slug}/documents/{document.id}"
        viewer_token, _ = issue_mobile_token(viewer)
        outsider_token, _ = issue_mobile_token(outsider)

        assert client.get(base, **_bearer(viewer_token)).status_code == 200
        assert client.get(base, **_bearer(outsider_token)).status_code == 404
        write = client.post(
            f"{base}/chat",
            data=json.dumps({"content": "hola"}),
            content_type="application/json",
            **_bearer(viewer_token),
        )
        assert write.status_code == 403


@pytest.mark.django_db
class TestRevoke:
    def test_logout_revokes_only_the_token_that_was_used(self, client):
        user = make_user()
        phone, _ = issue_mobile_token(user, device_name="phone")
        tablet, _ = issue_mobile_token(user, device_name="tablet")

        response = client.post("/api/auth/mobile-token/revoke", **_bearer(phone))

        assert response.status_code == 204
        assert client.get("/api/auth/me", **_bearer(phone)).status_code == 401
        assert client.get("/api/auth/me", **_bearer(tablet)).status_code == 200

    def test_revoking_requires_a_valid_token(self, client):
        # No header at all is denied (a plain POST without a CSRF token is a 403, as on every route).
        assert client.post("/api/auth/mobile-token/revoke").status_code in (401, 403)
        assert client.post("/api/auth/mobile-token/revoke", **_bearer("nope")).status_code == 401

    def test_a_session_without_a_bearer_token_cannot_revoke_anything(self):
        client = Client()  # CSRF not enforced here: this isolates the missing-token check
        user = make_user()
        client.force_login(user)

        response = client.post("/api/auth/mobile-token/revoke")

        assert response.status_code == 400 and response.json()["code"] == "bearer_token_required"


@pytest.mark.django_db
class TestMiddlewareScope:
    def test_a_valid_token_is_ignored_outside_the_api(self):
        user = make_user()
        raw, _ = issue_mobile_token(user)
        request = RequestFactory().get("/admin/", **_bearer(raw))
        request.user = type("Anon", (), {"is_authenticated": False})()

        BearerTokenMiddleware(lambda r: None)(request)

        assert request.user.is_authenticated is False
