"""Tests for the `seed_demo` management command (local-dev convenience)."""
import pytest
from django.core.management import call_command

from apps.organizations.constants import Role
from apps.organizations.management.commands.seed_demo import DEMO_ORG_SLUG, DEMO_USERS
from apps.organizations.models import Membership, Organization
from apps.users.models import User


@pytest.mark.django_db
class TestSeedDemo:
    def test_creates_demo_users_organization_and_memberships(self):
        call_command("seed_demo")

        for email, _ in DEMO_USERS:
            assert User.objects.filter(email__iexact=email).exists()

        organization = Organization.objects.get(slug=DEMO_ORG_SLUG)
        memberships = Membership.objects.for_organization(organization)
        assert memberships.count() == len(DEMO_USERS)
        assert memberships.get(user__email__iexact=DEMO_USERS[0][0]).role == Role.OWNER
        assert memberships.get(user__email__iexact=DEMO_USERS[1][0]).role == Role.EDITOR
        assert memberships.get(user__email__iexact=DEMO_USERS[2][0]).role == Role.VIEWER

    def test_each_demo_user_also_owns_an_auto_provisioned_personal_workspace(self):
        """design.md DD8: `register_user` now provisions a personal workspace
        for every demo user, in addition to the shared `acme-demo` org.
        """
        call_command("seed_demo")

        for email, _ in DEMO_USERS:
            user = User.objects.get(email__iexact=email)
            personal_orgs = Organization.objects.filter(memberships__user=user).exclude(
                slug=DEMO_ORG_SLUG
            )
            assert personal_orgs.count() == 1
            personal_membership = Membership.all_objects.get(
                organization=personal_orgs.first(), user=user
            )
            assert personal_membership.role == Role.OWNER

    def test_running_twice_does_not_duplicate_or_raise(self):
        call_command("seed_demo")
        call_command("seed_demo")

        assert User.objects.filter(
            email__iexact=DEMO_USERS[0][0]
        ).count() == 1
        organization = Organization.objects.get(slug=DEMO_ORG_SLUG)
        assert Membership.objects.for_organization(organization).count() == len(DEMO_USERS)
