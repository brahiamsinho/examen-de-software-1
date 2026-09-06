"""HTTP routers for the organizations domain (design.md's API Surface table).

Thin by construction: parse schema -> resolve membership -> check role ->
call one service function -> serialize. No business logic lives here.
"""
from django.http import Http404, HttpRequest
from ninja import Path, Router, Status
from ninja.security import django_auth

from apps.organizations import services
from apps.organizations.constants import Role
from apps.organizations.errors import (
    DuplicateMembershipError,
    DuplicateSlugError,
    LastOwnerError,
    OrganizationError,
    RoleNotAllowedError,
)
from apps.organizations.permissions import require_role, resolve_membership
from apps.organizations.schemas import (
    MemberAddIn,
    MembershipOut,
    OrganizationIn,
    OrganizationOut,
    OrganizationPatchIn,
    RoleChangeIn,
)

organizations_router = Router(auth=django_auth)
memberships_router = Router(auth=django_auth)


# --- organizations_router ------------------------------------------------

def _organization_out(organization, role: str | None = None) -> dict:
    return {
        "id": organization.id,
        "name": organization.name,
        "slug": organization.slug,
        "plan": organization.plan,
        "my_role": role,
    }


@organizations_router.get("", response=list[OrganizationOut])
def list_organizations(request: HttpRequest):
    memberships = request.user.memberships.select_related("organization")
    return [
        _organization_out(membership.organization, membership.role)
        for membership in memberships
    ]


@organizations_router.post("", response={201: OrganizationOut})
def create_organization(request: HttpRequest, payload: OrganizationIn):
    organization = services.create_organization(
        owner=request.user, name=payload.name, slug=payload.slug, plan=payload.plan
    )
    return Status(201, _organization_out(organization, Role.OWNER))


@organizations_router.get("/{org_slug}", response=OrganizationOut)
def get_organization(request: HttpRequest, org_slug: str):
    membership = resolve_membership(request, org_slug)
    return _organization_out(membership.organization, membership.role)


@organizations_router.patch("/{org_slug}", response=OrganizationOut)
def rename_organization(request: HttpRequest, org_slug: str, payload: OrganizationPatchIn):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER)
    organization = services.rename_organization(organization=membership.organization, name=payload.name)
    return _organization_out(organization, membership.role)


@organizations_router.delete("/{org_slug}", response={204: None})
def delete_organization(request: HttpRequest, org_slug: str):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER)
    services.delete_organization(organization=membership.organization)
    return Status(204, None)


# --- memberships_router ---------------------------------------------------
#
# `org_slug` lives in the mount prefix (`/orgs/{org_slug}/members`), not in
# each operation's own relative path, so the installed django-ninja 1.7
# does not auto-detect it as a path parameter (it would otherwise default
# to "query", which 404s every request). `Path[str]` makes the source
# explicit; Django's URL resolver already supplies the value via the
# mounted prefix regardless of this per-operation path model.

def _membership_out(membership) -> dict:
    return {
        "user_id": membership.user_id,
        "email": membership.user.email,
        "full_name": membership.user.full_name,
        "role": membership.role,
        "created_at": membership.created_at,
    }


@memberships_router.get("", response=list[MembershipOut])
def list_members(request: HttpRequest, org_slug: Path[str]):
    membership = resolve_membership(request, org_slug)
    members = services.list_memberships(organization=membership.organization)
    return [_membership_out(member) for member in members]


@memberships_router.post("", response={201: MembershipOut})
def add_member(request: HttpRequest, org_slug: Path[str], payload: MemberAddIn):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER)
    new_membership = services.add_member(
        organization=membership.organization, email=payload.email, role=payload.role
    )
    return Status(201, _membership_out(new_membership))


@memberships_router.patch("/{user_id}", response=MembershipOut)
def change_member_role(request: HttpRequest, org_slug: Path[str], user_id: str, payload: RoleChangeIn):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER)
    updated = services.change_member_role(
        organization=membership.organization, target_user_id=user_id, new_role=payload.role
    )
    return _membership_out(updated)


@memberships_router.delete("/{user_id}", response={204: None})
def remove_member(request: HttpRequest, org_slug: Path[str], user_id: str):
    membership = resolve_membership(request, org_slug)
    if str(membership.user_id) != str(user_id):
        require_role(membership, Role.OWNER)
    services.remove_member(organization=membership.organization, target_user_id=user_id)
    return Status(204, None)


# --- exception handlers (design.md DD6) -----------------------------------

_ERROR_STATUS_MAP: dict[type[OrganizationError], int] = {
    DuplicateSlugError: 409,
    DuplicateMembershipError: 409,
    LastOwnerError: 409,
    RoleNotAllowedError: 403,
}


def register_exception_handlers(api) -> None:
    def _handle_organization_error(request, exc: OrganizationError):
        status = _ERROR_STATUS_MAP.get(type(exc), 400)
        return api.create_response(request, {"detail": str(exc), "code": exc.code}, status=status)

    for exc_type in _ERROR_STATUS_MAP:
        api.add_exception_handler(exc_type, _handle_organization_error)

    def _handle_not_found(request, exc: Http404):
        return api.create_response(
            request, {"detail": "Not found.", "code": "not_found"}, status=404
        )

    api.add_exception_handler(Http404, _handle_not_found)
