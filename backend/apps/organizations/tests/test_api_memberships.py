"""Integration tests for `/api/orgs/{org_slug}/members/*`
(design.md API Surface table, organization-membership spec).
"""
import pytest

from apps.organizations.tests.factories import make_org_with_roles
from apps.users.tests.factories import make_user


@pytest.mark.django_db
class TestListMembers:
    def test_any_member_can_list(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(viewer)
        response = auth_client.get(f"/api/orgs/{organization.slug}/members")
        assert response.status_code == 200
        emails = {member["email"] for member in response.json()}
        assert owner.email in emails and editor.email in emails and viewer.email in emails

    def test_non_member_gets_404(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(outsider)
        response = auth_client.get(f"/api/orgs/{organization.slug}/members")
        assert response.status_code == 404


@pytest.mark.django_db
class TestAddMember:
    def test_owner_adds_existing_user(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        new_user = make_user()
        auth_client.force_login(owner)
        response = auth_client.post(
            f"/api/orgs/{organization.slug}/members",
            data={"email": new_user.email, "role": "EDITOR"},
            content_type="application/json",
        )
        assert response.status_code == 201
        assert response.json()["role"] == "EDITOR"

    def test_unregistered_email_fails_clearly(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.post(
            f"/api/orgs/{organization.slug}/members",
            data={"email": "ghost@example.com", "role": "EDITOR"},
            content_type="application/json",
        )
        assert response.status_code == 404
        assert response.json()["code"] == "user_not_found"

    def test_non_owner_cannot_add_members(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        new_user = make_user()
        auth_client.force_login(editor)
        response = auth_client.post(
            f"/api/orgs/{organization.slug}/members",
            data={"email": new_user.email, "role": "VIEWER"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_duplicate_membership_rejected(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.post(
            f"/api/orgs/{organization.slug}/members",
            data={"email": editor.email, "role": "VIEWER"},
            content_type="application/json",
        )
        assert response.status_code == 409
        assert response.json()["code"] == "duplicate_membership"


@pytest.mark.django_db
class TestRoleChange:
    def test_owner_changes_member_role(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.patch(
            f"/api/orgs/{organization.slug}/members/{editor.id}",
            data={"role": "VIEWER"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["role"] == "VIEWER"

    def test_demoting_sole_owner_fails(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.patch(
            f"/api/orgs/{organization.slug}/members/{owner.id}",
            data={"role": "EDITOR"},
            content_type="application/json",
        )
        assert response.status_code == 409
        assert response.json()["code"] == "last_owner"


@pytest.mark.django_db
class TestRemoveMember:
    def test_owner_removes_another_member(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.delete(f"/api/orgs/{organization.slug}/members/{editor.id}")
        assert response.status_code == 204

    def test_non_owner_self_removal_allowed(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(viewer)
        response = auth_client.delete(f"/api/orgs/{organization.slug}/members/{viewer.id}")
        assert response.status_code == 204

    def test_non_owner_cannot_remove_someone_else(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(editor)
        response = auth_client.delete(f"/api/orgs/{organization.slug}/members/{viewer.id}")
        assert response.status_code == 403

    def test_removing_sole_owner_fails(self, auth_client):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        response = auth_client.delete(f"/api/orgs/{organization.slug}/members/{owner.id}")
        assert response.status_code == 409
        assert response.json()["code"] == "last_owner"
