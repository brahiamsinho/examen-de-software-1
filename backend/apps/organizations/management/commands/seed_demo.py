"""Development-only seed data: demo users, a shared organization, and
memberships. Each demo user also gets an auto-provisioned personal workspace
(design.md DD8) — `register_user` provisions one organization per
registration, and this command registers through that same service.

Idempotent by construction (safe to run repeatedly, e.g. after a fresh
`docker compose up -d --build`): goes through the same domain services as a
real signup/invite, catching the "already exists" errors those services
raise instead of duplicating anything.
"""
from django.core.management.base import BaseCommand

from apps.organizations.constants import Plan, Role
from apps.organizations.errors import DuplicateMembershipError, DuplicateSlugError
from apps.organizations.models import Organization
from apps.organizations.services import add_member, create_organization
from apps.users.errors import DuplicateEmailError
from apps.users.models import User
from apps.users.services import register_user

DEMO_PASSWORD = "DemoPass123!"

DEMO_USERS = [
    ("owner@demo.com", "Ana Owner"),
    ("editor@demo.com", "Bruno Editor"),
    ("viewer@demo.com", "Carla Viewer"),
]

DEMO_ORG_NAME = "Acme Demo"
DEMO_ORG_SLUG = "acme-demo"

DEMO_MEMBERS = [
    (DEMO_USERS[1][0], Role.EDITOR),
    (DEMO_USERS[2][0], Role.VIEWER),
]


class Command(BaseCommand):
    help = (
        "Seed demo users (each with an auto-provisioned personal workspace), "
        "a shared organization, and memberships for local development."
    )

    def handle(self, *args, **options) -> None:
        for email, full_name in DEMO_USERS:
            try:
                register_user(email=email, password=DEMO_PASSWORD, full_name=full_name)
                self.stdout.write(self.style.SUCCESS(f"Created user {email}"))
            except DuplicateEmailError:
                self.stdout.write(f"User {email} already exists, skipping")

        owner = User.objects.get(email__iexact=DEMO_USERS[0][0])

        try:
            create_organization(
                owner=owner, name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG, plan=Plan.TEAM
            )
            self.stdout.write(self.style.SUCCESS(f"Created organization '{DEMO_ORG_SLUG}'"))
        except DuplicateSlugError:
            self.stdout.write(f"Organization '{DEMO_ORG_SLUG}' already exists, skipping")

        organization = Organization.objects.get(slug=DEMO_ORG_SLUG)

        for email, role in DEMO_MEMBERS:
            try:
                add_member(organization=organization, email=email, role=role)
                self.stdout.write(self.style.SUCCESS(f"Added {email} as {role}"))
            except DuplicateMembershipError:
                self.stdout.write(f"{email} is already a member, skipping")

        self.stdout.write(self.style.WARNING("\nDemo credentials (local dev only):"))
        for email, _ in DEMO_USERS:
            self.stdout.write(f"  {email} / {DEMO_PASSWORD}")
