"""HTTP-agnostic domain exceptions raised by the identity app.

Each carries a stable `code` string used by the (later PR) exception
handler mapping in `api.py`. Defined here — rather than inline in
`services.py` — because model-layer tests (duplicate constraints) already
need to assert on these types in this PR.
"""


class IdentityError(Exception):
    """Base class for all identity-domain errors."""

    code: str = "identity_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)


class DuplicateEmailError(IdentityError):
    code = "duplicate_email"


class PasswordPolicyError(IdentityError):
    code = "password_invalid"


class InvalidCredentialsError(IdentityError):
    code = "invalid_credentials"


class DuplicateSlugError(IdentityError):
    code = "duplicate_slug"


class UserNotFoundError(IdentityError):
    code = "user_not_found"


class DuplicateMembershipError(IdentityError):
    code = "duplicate_membership"


class LastOwnerError(IdentityError):
    code = "last_owner"


class RoleNotAllowedError(IdentityError):
    code = "forbidden"


class TenantScopeViolation(IdentityError):
    code = "tenant_scope_violation"
