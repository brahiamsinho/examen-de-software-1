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
    UserError,
    UserNotFoundError,
)
from apps.users.schemas import CsrfOut, LoginIn, RegisterIn, UserOut

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


# --- exception handlers (design.md DD6) -----------------------------------

_ERROR_STATUS_MAP: dict[type[UserError], int] = {
    DuplicateEmailError: 409,
    PasswordPolicyError: 400,
    InvalidCredentialsError: 401,
    UserNotFoundError: 404,
}


def register_exception_handlers(api) -> None:
    def _handle_user_error(request, exc: UserError):
        status = _ERROR_STATUS_MAP.get(type(exc), 400)
        return api.create_response(request, {"detail": str(exc), "code": exc.code}, status=status)

    for exc_type in _ERROR_STATUS_MAP:
        api.add_exception_handler(exc_type, _handle_user_error)
