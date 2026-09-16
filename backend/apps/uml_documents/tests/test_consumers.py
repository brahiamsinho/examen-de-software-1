"""WebSocket consumer authorization & broadcast relay (design.md DD3-DD5,
DD7, DD9).

Sync test bodies are wrapped with `asgiref.sync.async_to_sync` rather than
adding a `pytest-asyncio` dependency — Channels' own `WebsocketCommunicator`
needs an async caller, and `async_to_sync`/`sync_to_async` are already a
transitive dependency of `channels`/`daphne`. A real Redis broker is
swapped for Channels' in-process `InMemoryChannelLayer` via the
`settings` fixture: production Redis (design.md DD8) is infrastructure,
not something a unit test should depend on, and `InMemoryChannelLayer`
exercises the exact same `group_add`/`group_send`/`group_discard` code
paths.
"""
import datetime
import uuid

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.security.websocket import OriginValidator
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.test import Client

from apps.organizations.models import Membership
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import codec, services
from apps.uml_documents.routing import websocket_urlpatterns
from apps.users.tests.factories import make_user

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
_IN_MEMORY_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@pytest.fixture(autouse=True)
def _in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = _IN_MEMORY_LAYERS


def _router_app():
    return URLRouter(websocket_urlpatterns)


def _ws_path(org_slug: str, doc_id) -> str:
    return f"/ws/orgs/{org_slug}/documents/{doc_id}/"


async def _connect(org_slug: str, doc_id, user):
    communicator = WebsocketCommunicator(_router_app(), _ws_path(org_slug, doc_id))
    communicator.scope["user"] = user
    connected, close_code = await communicator.connect()
    return communicator, connected, close_code


@pytest.mark.django_db(transaction=True)
def test_authenticated_member_of_any_role_connects_and_joins_the_group():
    organization, owner, editor, viewer, _outsider = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Live", now=_NOW
    )

    async def scenario():
        for user in (owner, editor, viewer):
            communicator, connected, _ = await _connect(organization.slug, document.id, user)
            assert connected is True

            # Group join proof: a message sent to the document's group is
            # relayed back over this socket.
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                f"uml-doc-{document.id}",
                {"type": "document.update", "document": codec.document_out(document)},
            )
            payload = await communicator.receive_json_from()
            assert payload["type"] == "document.update"
            assert payload["document"]["id"] == str(document.id)

            await communicator.disconnect()

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_anonymous_connection_closes_4401():
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Live", now=_NOW
    )

    async def scenario():
        communicator, connected, close_code = await _connect(
            organization.slug, document.id, AnonymousUser()
        )
        assert connected is False
        assert close_code == 4401

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_non_member_closes_4404():
    organization, owner, *_rest = make_org_with_roles()
    outsider = make_user()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Live", now=_NOW
    )

    async def scenario():
        communicator, connected, close_code = await _connect(organization.slug, document.id, outsider)
        assert connected is False
        assert close_code == 4404

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_unknown_org_slug_closes_4404():
    _organization, owner, *_rest = make_org_with_roles()

    async def scenario():
        communicator, connected, close_code = await _connect("does-not-exist", uuid.uuid4(), owner)
        assert connected is False
        assert close_code == 4404

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_member_of_org_a_against_org_b_doc_id_closes_4404():
    organization_a, owner_a, *_rest = make_org_with_roles()
    organization_b, owner_b, *_rest = make_org_with_roles()
    document_b = services.create_document(
        organization=organization_b, owner_id=str(owner_b.id), name="Org B doc", now=_NOW
    )

    async def scenario():
        communicator, connected, close_code = await _connect(
            organization_a.slug, document_b.id, owner_a
        )
        assert connected is False
        assert close_code == 4404

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_unknown_doc_id_closes_4404():
    organization, owner, *_rest = make_org_with_roles()

    async def scenario():
        communicator, connected, close_code = await _connect(organization.slug, uuid.uuid4(), owner)
        assert connected is False
        assert close_code == 4404

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_foreign_origin_is_rejected_at_the_handshake(settings):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Live", now=_NOW
    )

    async def scenario():
        app = OriginValidator(_router_app(), ["http://localhost:3000"])
        communicator = WebsocketCommunicator(
            app,
            _ws_path(organization.slug, document.id),
            headers=[(b"origin", b"http://evil.example.com")],
        )
        communicator.scope["user"] = owner
        connected, _close = await communicator.connect()
        assert connected is False

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_membership_deleted_after_connect_closes_4403_with_no_payload():
    """design.md DD5: the group-message handler re-runs authorization
    before every relay. A member revoked after connecting must not receive
    the next broadcast — the socket closes 4403 instead.
    """
    organization, owner, _editor, viewer, _outsider = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Live", now=_NOW
    )

    async def scenario():
        communicator, connected, _ = await _connect(organization.slug, document.id, viewer)
        assert connected is True

        await sync_to_async(
            lambda: Membership.all_objects.filter(organization=organization, user=viewer).delete(),
            thread_sensitive=False,
        )()

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"uml-doc-{document.id}",
            {"type": "document.update", "document": codec.document_out(document)},
        )

        message = await communicator.receive_output()
        assert message["type"] == "websocket.close"
        assert message.get("code") == 4403

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_submitters_post_reaches_observers_socket_with_incremented_revision(
    django_capture_on_commit_callbacks,
):
    """End-to-end (task 4.9): client A's POST .../commands reaches client
    B's socket as `{"type": "document.update", "document": {…}}` with
    `revision` incremented exactly once, wiring Phase 2's
    `broadcast_document` to this consumer's group.
    """
    organization, owner, editor, viewer, _outsider = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Live", now=_NOW
    )

    def post_add_class():
        from django.db import connection

        try:
            auth_client = Client()
            auth_client.force_login(editor)
            with django_capture_on_commit_callbacks(execute=True):
                response = auth_client.post(
                    f"/api/orgs/{organization.slug}/documents/{document.id}/commands",
                    data={"type": "AddClass", "class_id": "c1", "name": "Order"},
                    content_type="application/json",
                )
            assert response.status_code == 200
        finally:
            connection.close()

    async def scenario():
        communicator, connected, _ = await _connect(organization.slug, document.id, viewer)
        assert connected is True

        await sync_to_async(post_add_class, thread_sensitive=False)()

        payload = await communicator.receive_json_from()
        assert payload["type"] == "document.update"
        assert payload["document"]["revision"] == document.revision + 1
        assert payload["document"]["id"] == str(document.id)

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_submitters_own_socket_also_receives_the_broadcast_it_triggered(
    django_capture_on_commit_callbacks,
):
    """Spec (realtime-document-sync, "Broadcast on Successful Command"):
    the server MUST broadcast to every client connected to the document's
    group, INCLUDING the client that submitted the command. The existing
    end-to-end test above only connects the observer (viewer) over
    WebsocketCommunicator; the submitter (editor) posts purely via a plain
    HTTP `Client()` and is never itself WS-connected, so submitter-inclusion
    was never proven at runtime (verify-report.md CRITICAL-1). This test
    connects BOTH the submitter and the observer over WebsocketCommunicator
    to the same document group and asserts both sockets receive the
    broadcast.
    """
    organization, owner, editor, viewer, _outsider = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Live", now=_NOW
    )

    def post_add_class():
        from django.db import connection

        try:
            auth_client = Client()
            auth_client.force_login(editor)
            with django_capture_on_commit_callbacks(execute=True):
                response = auth_client.post(
                    f"/api/orgs/{organization.slug}/documents/{document.id}/commands",
                    data={"type": "AddClass", "class_id": "c1", "name": "Order"},
                    content_type="application/json",
                )
            assert response.status_code == 200
        finally:
            connection.close()

    async def scenario():
        submitter_communicator, submitter_connected, _ = await _connect(
            organization.slug, document.id, editor
        )
        assert submitter_connected is True

        observer_communicator, observer_connected, _ = await _connect(
            organization.slug, document.id, viewer
        )
        assert observer_connected is True

        await sync_to_async(post_add_class, thread_sensitive=False)()

        submitter_payload = await submitter_communicator.receive_json_from()
        assert submitter_payload["type"] == "document.update"
        assert submitter_payload["document"]["revision"] == document.revision + 1
        assert submitter_payload["document"]["id"] == str(document.id)

        observer_payload = await observer_communicator.receive_json_from()
        assert observer_payload["type"] == "document.update"
        assert observer_payload["document"]["revision"] == document.revision + 1
        assert observer_payload["document"]["id"] == str(document.id)

    async_to_sync(scenario)()
