"""Plain builder functions for the organizations domain tests.

No `factory_boy` — matches Cycle 1's precedent (`apps/uml_modeling/tests/factories.py`),
so no new dependency is introduced. These builders construct rows directly
through the ORM (via `Membership.all_objects`, the unscoped escape-hatch
manager) rather than through `services.py`, since model-layer/tenant-scoping
tests must not depend on the service layer.

`make_user` is imported from `apps.users.tests.factories` — a normal
cross-app test import, since a `Membership` always needs a `User`.
"""
import itertools

from apps.organizations.constants import Role
from apps.organizations.models import Membership, Organization
from apps.users.models import User
from apps.users.tests.factories import make_user

_counter = itertools.count(1)


def _unique_suffix() -> int:
    return next(_counter)


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
    fixture shape most authorization tests need.
    """
    owner = make_user()
    organization = make_organization(owner=owner)
    editor_user = make_user()
    make_membership(organization=organization, user=editor_user, role=Role.EDITOR)
    viewer_user = make_user()
    make_membership(organization=organization, user=viewer_user, role=Role.VIEWER)
    outsider = make_user()
    return organization, owner, editor_user, viewer_user, outsider
