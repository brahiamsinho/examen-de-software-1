"""Tests for `resolve_membership` / `require_role` (design.md DD4,
tenant-isolation spec). Uses `RequestFactory` — no HTTP client needed.
"""
import pytest
from django.http import Http404
from django.test import RequestFactory

from apps.organizations import permissions
from apps.organizations.constants import Role
from apps.organizations.errors import RoleNotAllowedError
from apps.organizations.tests.factories import make_membership, make_org_with_roles, make_organization
from apps.users.tests.factories import make_user


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

    def test_resolves_strictly_from_the_path_slug_regardless_of_other_membership(self):
        """tenant-isolation spec, 'Tenant Key in the URL Path': the org is
        resolved strictly from the URL path segment. A user who belongs to
        two organizations must always get back the path's organization, no
        matter which of the two org_slugs is resolved first.
        """
        user = make_user()
        org_a = make_organization(owner=user)
        org_b = make_organization()
        make_membership(organization=org_b, user=user, role=Role.VIEWER)

        # Resolve org_b first, then org_a - order must not affect the result.
        request_b = RequestFactory().get(f"/api/orgs/{org_b.slug}")
        request_b.user = user
        membership_b = permissions.resolve_membership(request_b, org_b.slug)
        assert membership_b.organization_id == org_b.id
        assert membership_b.role == Role.VIEWER

        request_a = RequestFactory().get(f"/api/orgs/{org_a.slug}")
        request_a.user = user
        membership_a = permissions.resolve_membership(request_a, org_a.slug)
        assert membership_a.organization_id == org_a.id
        assert membership_a.role == Role.OWNER

        # And the reverse order gives the same, non-leaking result.
        membership_a_again = permissions.resolve_membership(request_a, org_a.slug)
        assert membership_a_again.organization_id == org_a.id
        assert membership_a_again.role == Role.OWNER


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
