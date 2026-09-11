"""HTTP router for the users domain.

Thin by construction: parse schema -> call one service function ->
serialize. No business logic lives here.
"""
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponseForbidden
from ninja import Router, Status
from ninja.security import django_auth
from ninja.utils import check_csrf

from apps.users import services
from apps.users.errors import (
    DuplicateEmailError,
    InvalidCredentialsError,
    PasswordPolicyError,
    ResendCooldownError,
    ResendRateLimitError,
    TokenExpiredError,
    TokenInvalidError,
    TokenUsedError,
    UserError,
    UserNotFoundError,
)
from apps.users.schemas import (
    CsrfOut,
    LoginIn,
    MessageOut,
    RegisterIn,
    ResetConfirmIn,
    ResetRequestIn,
    UserOut,
    VerifyIn,
)

# One constant response object for every branch of the anti-enumeration
# reset-request endpoint (design.md DD4): status code and body are both
# byte-identical regardless of whether the email matched an account, or
# whether the request was throttled.
_RESET_REQUEST_MESSAGE = {"message": "If that account exists, a reset email has been sent."}

auth_router = Router()


def _reject_unless_csrf_valid(request: HttpRequest) -> HttpResponseForbidden | None:
    """Manual double-submit CSRF enforcement for anonymous unsafe endpoints.

    `django_auth` (ninja's session auth) enforces CSRF automatically for
    authenticated requests (design.md DD2), but anonymous endpoints carry
    no auth class for ninja to hook CSRF into, so `register`/`login` check
    it explicitly here — this is exactly why `GET /auth/csrf` exists.
    """
    return check_csrf(request)


# --- auth_router --------------------------------------------------------

@auth_router.get("/csrf", response=CsrfOut, auth=None)
def get_csrf(request: HttpRequest):
    from django.middleware.csrf import get_token

    return {"csrf_token": get_token(request)}


@auth_router.post("/register", response={201: UserOut}, auth=None)
def register(request: HttpRequest, payload: RegisterIn):
    csrf_error = _reject_unless_csrf_valid(request)
    if csrf_error is not None:
        return csrf_error

    user = services.register_user(
        email=payload.email, password=payload.password, full_name=payload.full_name
    )
    login(request, user)
    return Status(201, user)


@auth_router.post("/login", response=UserOut, auth=None)
def login_view(request: HttpRequest, payload: LoginIn):
    csrf_error = _reject_unless_csrf_valid(request)
    if csrf_error is not None:
        return csrf_error

    user = services.authenticate_user(email=payload.email, password=payload.password)
    login(request, user)
    return user


@auth_router.post("/logout", response={204: None}, auth=django_auth)
def logout_view(request: HttpRequest):
    logout(request)
    return Status(204, None)


@auth_router.get("/me", response=UserOut, auth=django_auth)
def me(request: HttpRequest):
    return request.user


@auth_router.post("/verify-email", response={200: MessageOut}, auth=None)
def verify_email(request: HttpRequest, payload: VerifyIn):
    csrf_error = _reject_unless_csrf_valid(request)
    if csrf_error is not None:
        return csrf_error

    services.verify_email(token=payload.token)
    return {"message": "Your email has been verified."}


@auth_router.post("/resend-verification", response={202: MessageOut}, auth=django_auth)
def resend_verification(request: HttpRequest):
    services.resend_verification(user=request.user)
    return Status(202, {"message": "A new verification email has been sent."})


@auth_router.post("/password-reset/request", response={200: MessageOut}, auth=None)
def request_password_reset(request: HttpRequest, payload: ResetRequestIn):
    csrf_error = _reject_unless_csrf_valid(request)
    if csrf_error is not None:
        return csrf_error

    services.request_password_reset(email=payload.email)
    return _RESET_REQUEST_MESSAGE


@auth_router.post("/password-reset/confirm", response={200: MessageOut}, auth=None)
def confirm_password_reset(request: HttpRequest, payload: ResetConfirmIn):
    csrf_error = _reject_unless_csrf_valid(request)
    if csrf_error is not None:
        return csrf_error

    services.confirm_password_reset(token=payload.token, new_password=payload.password)
    return {"message": "Your password has been reset."}


# --- exception handlers (design.md DD6) -----------------------------------

_ERROR_STATUS_MAP: dict[type[UserError], int] = {
    DuplicateEmailError: 409,
    PasswordPolicyError: 400,
    InvalidCredentialsError: 401,
    UserNotFoundError: 404,
    TokenInvalidError: 400,
    TokenExpiredError: 400,
    TokenUsedError: 409,
    ResendCooldownError: 429,
    ResendRateLimitError: 429,
}


def register_exception_handlers(api) -> None:
    def _handle_user_error(request, exc: UserError):
        status = _ERROR_STATUS_MAP.get(type(exc), 400)
        return api.create_response(request, {"detail": str(exc), "code": exc.code}, status=status)

    for exc_type in _ERROR_STATUS_MAP:
        api.add_exception_handler(exc_type, _handle_user_error)
