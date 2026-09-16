"""
ASGI config for the config project.

Wraps the Django ASGI app in Channels' ProtocolTypeRouter so both plain HTTP
and websockets are served through the same ASGI application. The
"websocket" route serves `apps.uml_documents.routing.websocket_urlpatterns`
(design.md DD3), authenticated via `AuthMiddlewareStack` and origin-checked
via `OriginValidator` reusing `CORS_ALLOWED_ORIGINS` (DD9) — no CSRF
equivalent and no new env var, since the socket performs no writes.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
and https://channels.readthedocs.io/en/stable/installation.html
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# get_asgi_application() must be called before importing anything that
# imports models, per Channels' installation docs.
django_asgi_app = get_asgi_application()

# Imported after get_asgi_application() — `apps.uml_documents.routing`
# imports `consumers`, which imports models, per this file's own constraint.
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402
from django.conf import settings  # noqa: E402

from apps.uml_documents.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": OriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
            settings.CORS_ALLOWED_ORIGINS,
        ),
    }
)
