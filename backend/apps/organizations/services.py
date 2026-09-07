"""Invariant-bearing operations for the organizations domain (design.md DD3).

HTTP-agnostic, keyword-only, raising `errors.py` exceptions. Transaction
boundaries live here, not in views, so a later Channels consumer or
management command can call these functions directly.
"""
import secrets
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils.text import slugify

from apps.organizations.constants import Plan, Role
from apps.organizations.errors import (
    DuplicateMembershipError,
    DuplicateSlugError,
    LastOwnerError,
    OrganizationError,
)
from apps.organizations.models import Membership, Organization
from apps.users.errors import UserNotFoundError
from apps.users.models import User

_NAME_SUFFIX = "'s Workspace"
_NAME_MAX = 120
_SLUG_BASE_MAX = 40
_SLUG_ATTEMPTS = 5


def derive_workspace_name(*, source: str) -> str:
    """Pure (design.md DD1/D4). Truncates the SOURCE, never the composed
    string, so the result always ends with the suffix and is always
    <= 120 chars (Organization.name's max_length).
    """
    return f"{source[: _NAME_MAX - len(_NAME_SUFFIX)]}{_NAME_SUFFIX}"


def build_slug_base(*, source: str) -> str:
    """Pure (design.md DD1/D5 step 1). `slugify(source)[:40]`, or the
    literal `workspace` when the source slugifies to empty (e.g. a
    non-Latin name).
    """
    return slugify(source)[:_SLUG_BASE_MAX] or "workspace"


def generate_unique_slug(*, source: str) -> str:
    """D5 steps 2-4. Always suffixed; never tries the bare base, so the
    clean namespace stays available for deliberate organization creation
    (organization-tenancy § Server-Generated Organization Slug). Collision
    detection is an `.exists()` pre-check, not a retry loop around
    `create_organization`'s `IntegrityError` — looping over a caught error
    inside the caller's `atomic` block risks a poisoned transaction.
    """
    base = build_slug_base(source=source)
    for _ in range(_SLUG_ATTEMPTS):
        candidate = f"{base}-{secrets.token_hex(3)}"
        if not Organization.objects.filter(slug=candidate).exists():
            return candidate

    candidate = f"workspace-{secrets.token_hex(8)}"
    if not Organization.objects.filter(slug=candidate).exists():
        return candidate

    raise OrganizationError("Could not generate a unique organization slug.")


@transaction.atomic
def create_organization(*, owner: User, name: str, slug: str, plan: str = Plan.STARTER) -> Organization:
    """Create the `Organization` and the creator's `OWNER` `Membership`
    in the same transaction (organization-tenancy spec).
    """
    if Organization.objects.filter(slug=slug).exists():
        raise DuplicateSlugError(f"An organization with slug '{slug}' already exists.")

    try:
        organization = Organization.objects.create(name=name, slug=slug, plan=plan)
    except IntegrityError as exc:
        raise DuplicateSlugError(f"An organization with slug '{slug}' already exists.") from exc

    Membership.all_objects.create(user=owner, organization=organization, role=Role.OWNER)
    return organization


def rename_organization(*, organization: Organization, name: str) -> Organization:
    organization.name = name
    organization.save(update_fields=["name", "updated_at"])
    return organization


def delete_organization(*, organization: Organization) -> None:
    """Hard delete, cascading to every `Membership` row (organization-tenancy spec)."""
    organization.delete()


def list_user_organizations(*, user: User) -> QuerySet[Organization]:
    return Organization.objects.filter(memberships__user=user)


def add_member(*, organization: Organization, email: str, role: str) -> Membership:
    """Add an existing registered user by email lookup (organization-membership spec).
    Never invites unregistered addresses.
    """
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist as exc:
        raise UserNotFoundError(f"No user registered with email '{email}'.") from exc

    if Membership.objects.for_organization(organization).filter(user=user).exists():
        raise DuplicateMembershipError("This user is already a member of the organization.")

    try:
        return Membership.all_objects.create(user=user, organization=organization, role=role)
    except IntegrityError as exc:
        raise DuplicateMembershipError("This user is already a member of the organization.") from exc


@transaction.atomic
def change_member_role(*, organization: Organization, target_user_id: UUID, new_role: str) -> Membership:
    membership = (
        Membership.objects.for_organization(organization)
        .select_for_update()
        .get(user_id=target_user_id)
    )

    if new_role != membership.role:
        _assert_not_last_owner(organization=organization, membership=membership)

    membership.role = new_role
    membership.save(update_fields=["role", "updated_at"])
    return membership


@transaction.atomic
def remove_member(*, organization: Organization, target_user_id: UUID) -> None:
    membership = (
        Membership.objects.for_organization(organization)
        .select_for_update()
        .get(user_id=target_user_id)
    )

    _assert_not_last_owner(organization=organization, membership=membership)
    membership.delete()


def list_memberships(*, organization: Organization) -> QuerySet[Membership]:
    return Membership.objects.for_organization(organization).select_related("user")


def _assert_not_last_owner(*, organization: Organization, membership: Membership) -> None:
    """Shared invariant behind both the demote and the remove path
    (design.md DD3): an organization must always have at least one OWNER.
    """
    if membership.role != Role.OWNER:
        return

    remaining = (
        Membership.objects.for_organization(organization)
        .filter(role=Role.OWNER)
        .exclude(pk=membership.pk)
        .select_for_update()
        .count()
    )
    if remaining == 0:
        raise LastOwnerError("An organization must always have at least one OWNER.")
