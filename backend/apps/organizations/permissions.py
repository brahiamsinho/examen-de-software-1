"""Per-request membership resolution and role authorization
(design.md DD4, tenant-isolation spec).

`resolve_membership` is invoked as the first statement of every
tenant-scoped handler. Nothing else in the app decides authorization.
"""
from django.http import Http404, HttpRequest

from apps.organizations.constants import Role
from apps.organizations.errors import RoleNotAllowedError
from apps.organizations.models import Membership


def resolve_membership(request: HttpRequest, org_slug: str) -> Membership:
    """404 for an unknown slug AND for a non-member — indistinguishable
    by design (tenant-isolation spec's non-member response contract).
    """
    try:
        return (
            Membership.objects.unscoped()
            .select_related("organization", "user")
            .get(organization__slug=org_slug, user=request.user)
        )
    except Membership.DoesNotExist as exc:
        raise Http404("Organization not found") from exc


def require_role(membership: Membership, *allowed: Role) -> None:
    if membership.role not in allowed:
        raise RoleNotAllowedError("This action requires a different role.")
