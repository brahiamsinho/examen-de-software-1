"""
Django Ninja API root.

Mounts the identity domain's routers beside the pre-existing health check
(design.md's "API Surface" section).

Deviation from design.md: the design's exact `NinjaAPI(csrf=True)` call
assumes a `csrf` constructor kwarg that the installed django-ninja 1.7
does not expose (that kwarg existed in older/newer ninja releases, but
not this pinned range's resolved version). CSRF is enforced equivalently
per-endpoint instead: `django_auth` (ninja's session auth, used by every
authenticated router below) enforces the double-submit check by default
for any unsafe method, and the two anonymous unsafe endpoints
(`/auth/register`, `/auth/login`) call `ninja.utils.check_csrf` directly
(see `apps/identity/api.py`). Net effect is identical to the design's
intent: every unsafe method is CSRF-protected API-wide; `/health` and
every `GET` are unaffected.
"""
from ninja import NinjaAPI

from apps.identity.api import auth_router, memberships_router, organizations_router, register_exception_handlers

api = NinjaAPI()


@api.get("/health")
def health(request):
    return {"status": "ok"}


api.add_router("/auth", auth_router, tags=["auth"])
api.add_router("/orgs", organizations_router, tags=["organizations"])
api.add_router("/orgs/{org_slug}/members", memberships_router, tags=["memberships"])
register_exception_handlers(api)
