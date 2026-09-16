"""Read-only WebSocket fan-out for one document's live updates
(design.md DD3, DD4, DD5, DD7, DD9).

A sync `JsonWebsocketConsumer`, not async: every line of this codebase is
sync ORM, so a sync consumer runs in Channels' thread pool and can call the
membership/document queries directly — no `database_sync_to_async` wrapper
and no async fork of `resolve_membership_for_user`. The socket performs no
writes; `submit_command_view` (api.py) remains the only write transport.
"""
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.http import Http404

from apps.organizations.permissions import resolve_membership_for_user
from apps.uml_documents import services
from apps.uml_documents.schemas import DocumentOut


class DocumentConsumer(JsonWebsocketConsumer):
    """Joins group `uml-doc-{doc_id}` (design.md DD3). Authorization is
    membership only — deliberately NOT `require_role` (DD4): the WS is a
    read subscription mirroring `get_document_view`, which has no role
    gate either. Close codes: `4401` unauthenticated; `4404` unknown-org,
    non-member, or unknown-doc — indistinguishable, matching
    `resolve_membership`'s documented HTTP contract. `4403` closes a
    socket whose membership was revoked, re-checked on every relay (DD5).
    """

    def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            self.close(4401)
            return

        org_slug = self.scope["url_route"]["kwargs"]["org_slug"]
        doc_id = self.scope["url_route"]["kwargs"]["doc_id"]

        try:
            membership = resolve_membership_for_user(user, org_slug)
            services.get_document(organization=membership.organization, doc_id=doc_id)
        except Http404:
            self.close(4404)
            return

        self.org_slug = org_slug
        self.group_name = f"uml-doc-{doc_id}"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            async_to_sync(self.channel_layer.group_discard)(group_name, self.channel_name)

    def document_update(self, event):
        """Group-message handler (DD7 — the `group_send` `type` dispatches
        here by Channels' dot-to-underscore convention). Re-authorizes
        membership before every relay (DD5): a revoked member must stop
        receiving data at the exact moment data would leak.

        `event["document"]` is `codec.document_out(...)`'s raw dict — it
        still holds `UUID`/`datetime` values `json.dumps` rejects (DD6).
        Routing it through `DocumentOut` here is what makes the outgoing
        payload byte-identical to the `GET` response.
        """
        try:
            resolve_membership_for_user(self.scope["user"], self.org_slug)
        except Http404:
            self.close(4403)
            return
        document_out = DocumentOut.model_validate(event["document"]).model_dump(mode="json")
        self.send_json({"type": event["type"], "document": document_out})
