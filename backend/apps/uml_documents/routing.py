"""WS URL routing for the uml_documents domain (design.md DD3).

Mirrors the HTTP route `/api/orgs/{slug}/documents/{docId}` so the two
stay legible together.
"""
from django.urls import path

from apps.uml_documents import consumers

websocket_urlpatterns = [
    path(
        "ws/orgs/<str:org_slug>/documents/<uuid:doc_id>/",
        consumers.DocumentConsumer.as_asgi(),
    ),
]
