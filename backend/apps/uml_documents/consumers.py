"""Bidirectional WebSocket relay for one document's live updates
(design.md DD3-DD10).

A sync `JsonWebsocketConsumer`, not async: every line of this codebase is
sync ORM, so a sync consumer runs in Channels' thread pool and can call the
membership/document queries and `services.save_layout_position` directly —
no `database_sync_to_async` wrapper and no async fork of
`resolve_membership_for_user`. `submit_command_view` (api.py) remains the
only transport for `UmlCommand`s; this socket's only write is the layout
release path (DD8), which never touches the `UmlCommand` union.
"""
import uuid

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.http import Http404
from django.utils import timezone

from apps.organizations.constants import Role
from apps.organizations.errors import RoleNotAllowedError
from apps.organizations.permissions import require_role, resolve_membership_for_user
from apps.uml_documents import locks, services
from apps.uml_documents.schemas import DocumentOut
from apps.uml_modeling.documents import Position


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class DocumentConsumer(JsonWebsocketConsumer):
    """Joins group `uml-doc-{doc_id}` (design.md DD3). Connection
    authorization is membership only — deliberately NOT `require_role`
    (DD4 prior cycle, unchanged): the WS is a read subscription mirroring
    `get_document_view`, which has no role gate either. `receive_json`
    (DD6) re-resolves membership AND role on every inbound message, since
    the socket now writes. Close codes: `4401` unauthenticated; `4404`
    unknown-org, non-member, or unknown-doc — indistinguishable, matching
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
        self.doc_id = doc_id
        self.group_name = f"uml-doc-{doc_id}"
        self.token = uuid.uuid4().hex
        self.label = user.full_name or user.email
        self.held: set[str] = set()
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

        # DD10: a fresh joiner must learn what is already held before it
        # can grab anything — SCAN (never KEYS, which blocks the server).
        self.send_json(
            {
                "type": "node.locks",
                "locks": [
                    {"class_id": class_id, "owner_label": label, "mine": token == self.token}
                    for class_id, token, label in locks.snapshot(doc_id=doc_id)
                ],
            }
        )

    def disconnect(self, code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            async_to_sync(self.channel_layer.group_discard)(group_name, self.channel_name)

        # DD7: the fast path — release every lock this connection held and
        # tell the group, without waiting for TTL expiry. No durable write:
        # the last frame of an interrupted drag was never a chosen commit.
        # Guarded so a close before accept() (4401/4404) is a no-op.
        for class_id in getattr(self, "held", set()):
            if locks.release(doc_id=self.doc_id, class_id=class_id, token=self.token):
                async_to_sync(self.channel_layer.group_send)(
                    group_name, {"type": "node.unlocked", "class_id": class_id}
                )

    def receive_json(self, content, **kwargs):
        """Inbound client->server (design.md Message Contract): `node.claim`,
        `node.position`, `node.release`. An unknown `type`, a missing or
        non-string `class_id`, or (for position/release) a non-numeric
        `x`/`y` is dropped silently — the socket is never closed on a
        malformed frame (matching `api.py`'s bad-payload stance). DD6:
        role is re-resolved on every message; a `VIEWER` is silently
        refused, never closed, since it must keep receiving broadcasts.
        """
        try:
            membership = resolve_membership_for_user(self.scope["user"], self.org_slug)
        except Http404:
            self.close(4403)
            return

        message_type = content.get("type")
        class_id = content.get("class_id")
        if not isinstance(class_id, str):
            return

        try:
            require_role(membership, Role.OWNER, Role.EDITOR)
        except RoleNotAllowedError:
            return

        if message_type == "node.claim":
            self._handle_claim(class_id)
        elif message_type == "node.position":
            self._handle_position(content, class_id)
        elif message_type == "node.release":
            self._handle_release(membership, content, class_id)
        # else: unknown type, dropped silently.

    def _handle_claim(self, class_id: str) -> None:
        ok, owner_label = locks.claim(
            doc_id=self.doc_id, class_id=class_id, token=self.token, label=self.label
        )
        if ok:
            self.held.add(class_id)
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "node.locked",
                    "class_id": class_id,
                    "owner_label": self.label,
                    "owner_token": self.token,
                },
            )
        else:
            self.send_json(
                {"type": "node.claim_rejected", "class_id": class_id, "owner_label": owner_label}
            )

    def _handle_position(self, content: dict, class_id: str) -> None:
        x, y = content.get("x"), content.get("y")
        if not _is_number(x) or not _is_number(y):
            return
        # DD3: refresh doubles as the per-frame authorization check — only
        # the owning token may move this node; a non-owner is silently
        # rejected without a broadcast.
        if not locks.refresh(doc_id=self.doc_id, class_id=class_id, token=self.token):
            return
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                "type": "node.position",
                "class_id": class_id,
                "x": x,
                "y": y,
                "owner_token": self.token,
            },
        )

    def _handle_release(self, membership, content: dict, class_id: str) -> None:
        released = locks.release(doc_id=self.doc_id, class_id=class_id, token=self.token)
        if not released:
            return
        self.held.discard(class_id)

        x, y = content.get("x"), content.get("y")
        if _is_number(x) and _is_number(y):
            # DD8: the durable write, once per release — never per frame.
            services.save_layout_position(
                organization=membership.organization,
                doc_id=self.doc_id,
                class_id=class_id,
                position=Position(x=float(x), y=float(y)),
                now=timezone.now(),
            )
        # else: null/omitted coordinates (the RemoveClass-mid-drag case) —
        # release the lock and skip the durable write entirely.

        async_to_sync(self.channel_layer.group_send)(
            self.group_name, {"type": "node.unlocked", "class_id": class_id}
        )

    def node_locked(self, event):
        """Group handler for `node.claim`'s broadcast (DD9). Re-derives
        `mine` per connection and never forwards `owner_token` to the
        client — this IS the claim-accepted ack for the winning claimant.
        """
        self.send_json(
            {
                "type": "node.locked",
                "class_id": event["class_id"],
                "owner_label": event["owner_label"],
                "mine": event["owner_token"] == self.token,
            }
        )

    def node_position(self, event):
        """Group handler for a live drag frame (DD9, DD11 backend half)."""
        self.send_json(
            {
                "type": "node.position",
                "class_id": event["class_id"],
                "x": event["x"],
                "y": event["y"],
                "mine": event["owner_token"] == self.token,
            }
        )

    def node_unlocked(self, event):
        self.send_json({"type": "node.unlocked", "class_id": event["class_id"]})

    def document_update(self, event):
        """Group-message handler (DD7 — the `group_send` `type` dispatches
        here by Channels' dot-to-underscore convention). Re-authorizes
        membership before every relay (DD5): a revoked member must stop
        receiving data at the exact moment data would leak.

        `event["document"]` is already JSON-safe — `services.broadcast_document`
        serializes it through `DocumentOut` before `group_send`, since that
        call crosses channels_redis' msgpack transport and would break on a
        raw `UUID`/`datetime` before this handler ever runs. Re-validating
        through `DocumentOut` here is idempotent and keeps this payload
        byte-identical to the `GET` response by construction (DD6).
        """
        try:
            resolve_membership_for_user(self.scope["user"], self.org_slug)
        except Http404:
            self.close(4403)
            return
        document_out = DocumentOut.model_validate(event["document"]).model_dump(mode="json")
        self.send_json({"type": event["type"], "document": document_out})
