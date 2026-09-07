"""Tenant-scoping contract (DD1 / tenant-isolation spec): `for_organization()`
is the only normal access path, the default manager raises, `.unscoped()` is
the explicit escape hatch, and reverse related access still works.
"""
import pytest

from apps.organizations.constants import Role
from apps.organizations.errors import TenantScopeViolation
from apps.organizations.models import Membership, Organization
from apps.users.models import User


@pytest.mark.django_db
def test_for_organization_returns_only_that_organizations_rows():
    user_a = User.objects.create_user(email="ivan@example.com", password="a-strong-pass-10")
    user_b = User.objects.create_user(email="judy@example.com", password="a-strong-pass-11")
    org_a = Organization.objects.create(name="Org A", slug="org-a")
    org_b = Organization.objects.create(name="Org B", slug="org-b")
    Membership.all_objects.create(user=user_a, organization=org_a, role=Role.OWNER)
    Membership.all_objects.create(user=user_b, organization=org_b, role=Role.OWNER)

    scoped = Membership.objects.for_organization(org_a)

    assert scoped.count() == 1
    assert scoped.get().organization_id == org_a.id


@pytest.mark.django_db
def test_default_manager_raises_tenant_scope_violation():
    with pytest.raises(TenantScopeViolation):
        Membership.objects.all()


@pytest.mark.django_db
def test_unscoped_is_the_explicit_escape_hatch_across_organizations():
    user_a = User.objects.create_user(email="karl@example.com", password="a-strong-pass-12")
    user_b = User.objects.create_user(email="lena@example.com", password="a-strong-pass-13")
    org_a = Organization.objects.create(name="Org A", slug="org-a")
    org_b = Organization.objects.create(name="Org B", slug="org-b")
    Membership.all_objects.create(user=user_a, organization=org_a, role=Role.OWNER)
    Membership.all_objects.create(user=user_b, organization=org_b, role=Role.OWNER)

    everything = Membership.objects.unscoped()

    assert everything.count() == 2


@pytest.mark.django_db
def test_reverse_related_access_from_organization_instance_still_works():
    user = User.objects.create_user(email="mia@example.com", password="a-strong-pass-14")
    org = Organization.objects.create(name="Org A", slug="org-a")
    Membership.all_objects.create(user=user, organization=org, role=Role.OWNER)

    memberships = org.memberships.all()

    assert memberships.count() == 1
