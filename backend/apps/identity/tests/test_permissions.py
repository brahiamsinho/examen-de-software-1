"""Tests for `resolve_membership` / `require_role` (design.md DD4,
tenant-isolation spec). Uses `RequestFactory` — no HTTP client needed.
"""
import pytest
from django.http import Http404
from django.test import RequestFactory

from apps.identity import permissions
from apps.identity.constants import Role
from apps.identity.errors import RoleNotAllowedError
from apps.identity.tests.factories import make_org_with_roles, make_user


@pytest.mark.django_db
class TestResolveMembership:
    def test_member_resolves_own_membership(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()
        request = RequestFactory().get(f"/api/orgs/{org.slug}")
        request.user = owner

        membership = permissions.resolve_membership(request, org.slug)

        assert membership.user_id == owner.id
        assert membership.organization_id == org.id
        assert membership.role == Role.OWNER

    def test_unknown_slug_raises_404(self):
        outsider = make_user()
        request = RequestFactory().get("/api/orgs/does-not-exist")
        request.user = outsider

        with pytest.raises(Http404):
            permissions.resolve_membership(request, "does-not-exist")

    def test_non_member_raises_404(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()
        request = RequestFactory().get(f"/api/orgs/{org.slug}")
        request.user = outsider

        with pytest.raises(Http404):
            permissions.resolve_membership(request, org.slug)


@pytest.mark.django_db
class TestRequireRole:
    def test_allowed_role_passes(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()
        request = RequestFactory().get(f"/api/orgs/{org.slug}")
        request.user = owner
        membership = permissions.resolve_membership(request, org.slug)

        permissions.require_role(membership, Role.OWNER)  # must not raise

    def test_editor_rejected_from_owner_only_action(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()
        request = RequestFactory().get(f"/api/orgs/{org.slug}")
        request.user = editor
        membership = permissions.resolve_membership(request, org.slug)

        with pytest.raises(RoleNotAllowedError):
            permissions.require_role(membership, Role.OWNER)

    def test_viewer_rejected_from_owner_only_action(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()
        request = RequestFactory().get(f"/api/orgs/{org.slug}")
        request.user = viewer
        membership = permissions.resolve_membership(request, org.slug)

        with pytest.raises(RoleNotAllowedError):
            permissions.require_role(membership, Role.OWNER)
