"""
Django Ninja API root.

No business endpoints exist yet (see backend/apps/); this only proves the
Ninja wiring works end-to-end with a minimal health check.
"""
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/health")
def health(request):
    return {"status": "ok"}
