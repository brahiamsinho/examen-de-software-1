"""Accept the mobile bearer token on the API (GitHub #19).

Every router authenticates with ninja's `django_auth`, which reads
`request.user` and, for session cookies, enforces CSRF. This middleware sets
`request.user` from a valid `Authorization: Bearer <token>` header and marks
the request CSRF-exempt, so no router or handler changes. A browser never
sends that header on its own, so waiving CSRF for it is safe.

A well-formed bearer header whose token is unknown, expired or revoked is
refused with 401 on EVERY method. Falling through to the session/CSRF path
would turn an expired token into a confusing 403 on writes, and the phone
could not tell "log in again" from "you lack the role". Requests without a
bearer header are untouched (a plain session still needs its CSRF token).
Scope is limited to `/api/` so the token cannot open the Django admin.
"""
from django.http import HttpRequest, JsonResponse

from apps.users.mobile_tokens import resolve_mobile_token

_API_PREFIX = "/api/"


def bearer_token(request: HttpRequest) -> str | None:
    """The raw token of a well-formed `Authorization: Bearer <token>` header."""
    parts = request.META.get("HTTP_AUTHORIZATION", "").split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


class BearerTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if request.path.startswith(_API_PREFIX):
            raw = bearer_token(request)
            if raw is not None:
                user = resolve_mobile_token(raw)
                if user is None:
                    response = JsonResponse(
                        {"detail": "Invalid or expired token.", "code": "invalid_token"}, status=401
                    )
                    response["WWW-Authenticate"] = "Bearer"
                    return response
                request.user = user
                request._ninja_csrf_exempt = True  # read by ninja's SessionAuth
                request._dont_enforce_csrf_checks = True  # read by Django's CSRF check
        return self.get_response(request)
