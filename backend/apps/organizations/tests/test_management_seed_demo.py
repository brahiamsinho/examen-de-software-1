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

    def test_running_twice_does_not_duplicate_or_raise(self):
        call_command("seed_demo")
        call_command("seed_demo")

        assert User.objects.filter(
            email__iexact=DEMO_USERS[0][0]
        ).count() == 1
        organization = Organization.objects.get(slug=DEMO_ORG_SLUG)
        assert Membership.objects.for_organization(organization).count() == len(DEMO_USERS)
