"""HTTP-agnostic domain exceptions raised by the organizations app.

Each carries a stable `code` string used by the exception handler mapping
in `api.py`. Defined here — rather than inline in `services.py` — because
model-layer tests (duplicate constraints) already need to assert on these
types.
"""


class OrganizationError(Exception):
    """Base class for all organization-domain errors."""

    code: str = "organization_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)


class DuplicateSlugError(OrganizationError):
    code = "duplicate_slug"


class DuplicateMembershipError(OrganizationError):
    code = "duplicate_membership"


class LastOwnerError(OrganizationError):
    code = "last_owner"


class RoleNotAllowedError(OrganizationError):
    code = "forbidden"


class TenantScopeViolation(OrganizationError):
    code = "tenant_scope_violation"
