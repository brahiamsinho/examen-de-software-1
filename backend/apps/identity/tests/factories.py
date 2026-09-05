"""Plain builder functions for the identity domain tests.

No `factory_boy` — matches Cycle 1's precedent (`apps/uml_modeling/tests/factories.py`),
so no new dependency is introduced. These builders construct rows directly
through the ORM (via `Membership.all_objects`, the unscoped escape-hatch
manager) rather than through `services.py`, since the service layer is a
later PR's deliverable and model-layer/tenant-scoping tests must not depend
on it.
"""
import itertools

from apps.identity.constants import Role
from apps.identity.models import Membership, Organization, User

_counter = itertools.count(1)


def _unique_suffix() -> int:
    return next(_counter)


def make_user(*, email: str | None = None, password: str = "a-strong-pass-0", full_name: str = "") -> User:
    email = email or f"user{_unique_suffix()}@example.com"
    return User.objects.create_user(email=email, password=password, full_name=full_name)


def make_organization(
    *,
    owner: User | None = None,
    name: str | None = None,
    slug: str | None = None,
    plan: str = "STARTER",
) -> Organization:
    suffix = _unique_suffix()
    org = Organization.objects.create(
        name=name or f"Organization {suffix}",
        slug=slug or f"org-{suffix}",
        plan=plan,
    )
    owner = owner or make_user()
    Membership.all_objects.create(user=owner, organization=org, role=Role.OWNER)
    return org


def make_membership(*, organization: Organization, user: User | None = None, role: str = Role.EDITOR) -> Membership:
    user = user or make_user()
    return Membership.all_objects.create(user=user, organization=organization, role=role)


def make_org_with_roles():
    """Returns `(organization, owner, editor, viewer, outsider)` — the
    fixture shape most authorization tests (later PRs) need.
    """
    owner = make_user()
    organization = make_organization(owner=owner)
    editor_user = make_user()
    make_membership(organization=organization, user=editor_user, role=Role.EDITOR)
    viewer_user = make_user()
    make_membership(organization=organization, user=viewer_user, role=Role.VIEWER)
    outsider = make_user()
    return organization, owner, editor_user, viewer_user, outsider
