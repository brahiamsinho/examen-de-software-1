"""
ASGI config for the config project.

Wraps the Django ASGI app in Channels' ProtocolTypeRouter so both plain HTTP
and (eventually) websockets are served through the same ASGI application.
No websocket consumers exist yet, so the "websocket" route is an empty
URLRouter placeholder — it will be populated once realtime features are
designed.

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

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter([]),
    }
)
