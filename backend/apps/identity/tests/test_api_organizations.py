"""Integration tests for `/api/orgs/*` (design.md API Surface table).

Covers CRUD status codes and the 404-not-403 non-member contract
(tenant-isolation spec).
"""
import pytest

from apps.identity.tests.factories import make_org_with_roles, make_user


@pytest.mark.django_db
class TestListAndCreate:
    def test_list_requires_authentication(self, auth_client):
        response = auth_client.get("/api/orgs")
        assert response.status_code == 401

    def test_list_returns_only_callers_memberships(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.get("/api/orgs")
        assert response.status_code == 200
        slugs = [item["slug"] for item in response.json()]
        assert slugs == [organization.slug]

    def test_create_makes_caller_owner(self, auth_client):
        user = make_user()
        auth_client.force_login(user)
        response = auth_client.post(
            "/api/orgs",
            data={"name": "Acme", "slug": "acme"},
            content_type="application/json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["slug"] == "acme"
        assert body["plan"] == "STARTER"
        assert body["my_role"] == "OWNER"

    def test_create_duplicate_slug_rejected(self, auth_client):
        make_org_with_roles()
        existing = make_org_with_roles()[0]
        user = make_user()
        auth_client.force_login(user)
        response = auth_client.post(
            "/api/orgs",
            data={"name": "Dup", "slug": existing.slug},
            content_type="application/json",
        )
        assert response.status_code == 409
        assert response.json()["code"] == "duplicate_slug"


@pytest.mark.django_db
class TestReadRenameDelete:
    def test_member_reads_organization(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(editor)
        response = auth_client.get(f"/api/orgs/{organization.slug}")
        assert response.status_code == 200
        assert response.json()["slug"] == organization.slug

    def test_non_member_gets_404_not_403(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(outsider)
        response = auth_client.get(f"/api/orgs/{organization.slug}")
        assert response.status_code == 404

    def test_unknown_slug_gets_404_indistinguishable(self, auth_client):
        user = make_user()
        auth_client.force_login(user)
        response = auth_client.get("/api/orgs/does-not-exist")
        assert response.status_code == 404

    def test_owner_renames_organization(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.patch(
            f"/api/orgs/{organization.slug}",
            data={"name": "Renamed"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed"

    def test_non_owner_rename_rejected(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(editor)
        response = auth_client.patch(
            f"/api/orgs/{organization.slug}",
            data={"name": "Renamed"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_owner_deletes_organization(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.delete(f"/api/orgs/{organization.slug}")
        assert response.status_code == 204

    def test_non_owner_delete_rejected(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(viewer)
        response = auth_client.delete(f"/api/orgs/{organization.slug}")
        assert response.status_code == 403
