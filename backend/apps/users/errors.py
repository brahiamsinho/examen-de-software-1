"""HTTP-agnostic domain exceptions raised by the users app.

Each carries a stable `code` string used by the exception handler mapping
in `api.py`. Defined here — rather than inline in `services.py` — because
model-layer tests (duplicate constraints) already need to assert on these
types.
"""


class UserError(Exception):
    """Base class for all user-domain errors."""

    code: str = "user_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)


class DuplicateEmailError(UserError):
    code = "duplicate_email"


class PasswordPolicyError(UserError):
    code = "password_invalid"


class InvalidCredentialsError(UserError):
    code = "invalid_credentials"


class UserNotFoundError(UserError):
    code = "user_not_found"
