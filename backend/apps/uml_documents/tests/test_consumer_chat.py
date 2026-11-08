"""`chat.message` reaches every member's socket and is dropped for a revoked
member (issue #16). Same harness as `test_consumer_proposals.py`."""
import datetime

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from apps.organizations.models import Membership
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services
from apps.uml_documents.routing import websocket_urlpatterns

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


@pytest.fixture(autouse=True)
def _in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


async def _connect(organization, document, user):
    communicator = WebsocketCommunicator(
        URLRouter(websocket_urlpatterns), f"/ws/orgs/{organization.slug}/documents/{document.id}/"
    )
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected
    await communicator.receive_json_from()  # the initial `node.locks` snapshot
    return communicator


@pytest.mark.django_db(transaction=True)
def test_every_member_receives_a_chat_message_including_a_viewer():
    organization, owner, editor, viewer, _outsider = make_org_with_roles()
    document = services.create_document(organization=organization, owner_id=str(owner.id), name="Live", now=_NOW)
    event = {"type": "chat.message", "message": {"id": 1, "content": "hola", "author": "Ana", "is_ai": False}}

    async def scenario():
        sockets = [await _connect(organization, document, user) for user in (owner, editor, viewer)]
        await get_channel_layer().group_send(f"uml-doc-{document.id}", event)
        for socket in sockets:
            assert await socket.receive_json_from() == event
            await socket.disconnect()

    async_to_sync(scenario)()


@pytest.mark.django_db(transaction=True)
def test_a_member_removed_after_connecting_gets_no_chat_and_is_closed():
    organization, owner, editor, *_ = make_org_with_roles()
    document = services.create_document(organization=organization, owner_id=str(owner.id), name="Live", now=_NOW)

    async def scenario():
        socket = await _connect(organization, document, editor)
        await sync_to_async(Membership.objects.for_organization(organization).filter(user=editor).delete)()
        await get_channel_layer().group_send(
            f"uml-doc-{document.id}", {"type": "chat.message", "message": {"content": "secret"}}
        )
        output = await socket.receive_output()
        assert output["type"] == "websocket.close" and output["code"] == 4403

    async_to_sync(scenario)()
