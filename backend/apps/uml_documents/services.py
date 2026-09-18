"""Service layer for the uml_documents domain (design.md's Data Flow).

The only caller of `apps.uml_commands.dispatcher.apply` and the only
place that reassembles a full `ProjectDocument` from a `UmlDocument` row
+ decoded `codec` triple (DD5). Every lookup goes through
`UmlDocument.objects.for_organization(organization)` — never through the
raising default manager or `all_objects` directly (Tenant Scoping on
Every Access).
"""
import datetime
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.http import Http404

from apps.organizations.models import Organization
from apps.uml_commands import commands
from apps.uml_commands.commands import UmlCommand
from apps.uml_commands.dispatcher import CommandResult, apply
from apps.uml_documents import codec, schemas
from apps.uml_documents.errors import InvalidCommandPayloadError
from apps.uml_documents.models import UmlDocument
from apps.uml_modeling.documents import DiagramLayout, Position, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import (
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlOperation,
    Visibility,
)
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import parse_multiplicity


def _to_project_document(row: UmlDocument) -> ProjectDocument:
    metadata, model, layout = codec.from_json(row.data)
    return ProjectDocument(
        id=row.id,
        metadata=metadata,
        owner_id=row.owner_id,
        model=model,
        layout=layout,
        created_at=row.created_at,
        updated_at=row.updated_at,
        revision=row.revision,
    )


def _save(row: UmlDocument, document: ProjectDocument) -> None:
    row.revision = document.revision
    row.updated_at = document.updated_at
    row.data = codec.to_json(document.metadata, document.model, document.layout)
    row.save()


def _get_row(
    *, organization: Organization, doc_id: UUID, for_update: bool = False
) -> UmlDocument:
    """`for_update=True` chains `.select_for_update()` AFTER the tenant
    filter (design.md DD1) — the lock is taken on the already-scoped row,
    it never widens the queryset. `for_update` defaults to `False` because
    this function also backs `get_document`, whose GET view runs outside
    any transaction; an unconditional lock there would raise
    `TransactionManagementError`.
    """
    qs = UmlDocument.objects.for_organization(organization)
    if for_update:
        qs = qs.select_for_update()
    try:
        return qs.get(id=doc_id)
    except UmlDocument.DoesNotExist as exc:
        raise Http404("Document not found") from exc


def broadcast_document(*, document: ProjectDocument) -> None:
    """Fans a `document.update` event out to every socket subscribed to
    this document's group (design.md DD2/DD3/DD6/DD7). Always called via
    `transaction.on_commit`, never inline, so a reader can always `SELECT`
    the revision being broadcast.

    `channel_layer.group_send` crosses channels_redis' msgpack transport in
    production — a boundary distinct from (and earlier than) the
    `json.dumps` the consumer's `send_json` sees. `codec.document_out`
    returns raw `UUID`/`datetime` values, so the payload is pre-serialized
    through `schemas.DocumentOut` here, before it ever reaches `group_send`,
    not just on the consumer's receiving side.
    """
    channel_layer = get_channel_layer()
    payload = schemas.DocumentOut.model_validate(codec.document_out(document)).model_dump(
        mode="json"
    )
    async_to_sync(channel_layer.group_send)(
        f"uml-doc-{document.id}",
        {"type": "document.update", "document": payload},
    )


def create_document(
    *, organization: Organization, owner_id: str, name: str, now: datetime.datetime
) -> ProjectDocument:
    data = codec.to_json(ProjectMetadata(name=name), CanonicalUmlModel(), DiagramLayout())
    row = UmlDocument.objects.for_organization(organization).create(
        organization=organization,
        owner_id=owner_id,
        revision=1,
        created_at=now,
        updated_at=now,
        data=data,
    )
    return _to_project_document(row)


def get_document(*, organization: Organization, doc_id: UUID) -> ProjectDocument:
    row = _get_row(organization=organization, doc_id=doc_id)
    return _to_project_document(row)


def list_documents(*, organization: Organization) -> list[ProjectDocument]:
    """Newest-updated first — `UmlDocument.Meta` declares no `ordering`,
    so the order is stated here or it is undefined (design.md DD1).
    """
    rows = UmlDocument.objects.for_organization(organization).order_by("-updated_at")
    return [_to_project_document(row) for row in rows]


@transaction.atomic
def submit_command(
    *, organization: Organization, doc_id: UUID, command: UmlCommand, now: datetime.datetime
) -> CommandResult:
    """Serialized under a per-document row lock (design.md DD1): the
    decorator opens the transaction `select_for_update()` needs, matching
    `users/services.py:40`/`organizations/services.py:68` style. On
    success, the resulting document is broadcast to the document's group
    once the transaction actually commits (DD2) — never inline, which
    would publish a revision no reader can yet `SELECT`.
    """
    row = _get_row(organization=organization, doc_id=doc_id, for_update=True)
    document = _to_project_document(row)
    result = apply(document, command, now=now)
    _save(row, result.document)
    transaction.on_commit(lambda: broadcast_document(document=result.document))
    return result


@transaction.atomic
def save_layout_position(
    *,
    organization: Organization,
    doc_id: UUID,
    class_id: str,
    position: Position,
    now: datetime.datetime,
) -> ProjectDocument:
    """Sibling to `submit_command`, deliberately NOT routed through
    `dispatcher.apply()` or any `UmlCommand` variant (design.md DD8):
    ephemeral node claims never touch Postgres or `revision`, but a
    released drag's final position is durable, and this is that write.
    Takes the same `@transaction.atomic` + `_get_row(for_update=True)`
    row lock `submit_command` already takes, so the two write paths can
    never race each other on the same document.

    A `class_id` absent from the document's current model (removed by a
    `RemoveClass` mid-drag) returns the document UNCHANGED — no write, no
    `revision` bump (DD8's `RemoveClass` case). Every persisted entry
    whose class id is no longer live is pruned on every successful call,
    which is self-healing and needs no migration.
    """
    row = _get_row(organization=organization, doc_id=doc_id, for_update=True)
    document = _to_project_document(row)
    live = {c.id for c in document.model.classes}
    target = ElementId(class_id)
    if target not in live:
        return document
    positions = {cid: p for cid, p in document.layout.positions.items() if cid in live}
    positions[target] = position
    updated = document.with_layout(DiagramLayout(positions=positions), now=now)
    _save(row, updated)
    transaction.on_commit(lambda: broadcast_document(document=updated))
    return updated


def command_from_payload(payload: "schemas.CommandIn") -> UmlCommand:
    """Convert a validated `CommandIn` payload into a real `UmlCommand`.

    The outer `{type, ...}` envelope is already validated by pydantic's
    discriminated union before this runs. The inner shapes this function
    decodes (`attribute.type`, a relationship end's `multiplicity`) are
    loosely typed (`str | dict`) and validated here by hand — any
    `KeyError`/`ValueError`/`TypeError` from a malformed inner shape is
    normalized to `InvalidCommandPayloadError`, mapped to a 422 by
    `api.py`'s exception handler, so a bad client payload never surfaces
    as an unhandled 500.
    """
    try:
        return _command_from_payload(payload)
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidCommandPayloadError(f"Malformed command payload: {exc}") from exc


def _command_from_payload(payload: "schemas.CommandIn") -> UmlCommand:
    if isinstance(payload, schemas.AddClassIn):
        return commands.AddClass(class_id=ElementId(payload.class_id), name=payload.name)
    if isinstance(payload, schemas.RemoveClassIn):
        return commands.RemoveClass(class_id=ElementId(payload.class_id))
    if isinstance(payload, schemas.RenameClassIn):
        return commands.RenameClass(class_id=ElementId(payload.class_id), new_name=payload.new_name)
    if isinstance(payload, schemas.AddAttributeIn):
        return commands.AddAttribute(
            class_id=ElementId(payload.class_id),
            attribute=_attribute_from_schema(payload.attribute),
        )
    if isinstance(payload, schemas.RemoveAttributeIn):
        return commands.RemoveAttribute(
            class_id=ElementId(payload.class_id), attribute_id=ElementId(payload.attribute_id)
        )
    if isinstance(payload, schemas.AddOperationIn):
        return commands.AddOperation(
            class_id=ElementId(payload.class_id),
            operation=_operation_from_schema(payload.operation),
        )
    if isinstance(payload, schemas.RemoveOperationIn):
        return commands.RemoveOperation(
            class_id=ElementId(payload.class_id), operation_id=ElementId(payload.operation_id)
        )
    if isinstance(payload, schemas.AddRelationshipIn):
        return commands.AddRelationship(relationship=_relationship_from_schema(payload.relationship))
    if isinstance(payload, schemas.RemoveRelationshipIn):
        return commands.RemoveRelationship(relationship_id=ElementId(payload.relationship_id))
    raise ValueError(f"Unknown command payload type: {payload!r}")


def _attribute_from_schema(attribute_in: "schemas.UmlAttributeIn") -> UmlAttribute:
    return UmlAttribute(
        id=ElementId(attribute_in.id),
        name=attribute_in.name,
        type=codec._decode_attribute_type(attribute_in.type),
        visibility=Visibility(attribute_in.visibility),
    )


def _operation_from_schema(operation_in: "schemas.UmlOperationIn") -> UmlOperation:
    return UmlOperation(
        id=ElementId(operation_in.id),
        name=operation_in.name,
        return_type=codec._decode_attribute_type(operation_in.return_type)
        if operation_in.return_type is not None
        else None,
        parameters=(),
        visibility=Visibility(operation_in.visibility),
    )


def _relationship_from_schema(relationship_in: "schemas.RelationshipIn") -> Relationship:
    return Relationship(
        id=ElementId(relationship_in.id),
        kind=RelationshipKind(relationship_in.kind),
        source=_relationship_end_from_schema(relationship_in.source),
        target=_relationship_end_from_schema(relationship_in.target),
        name=relationship_in.name,
    )


def _relationship_end_from_schema(end_in: "schemas.RelationshipEndIn") -> RelationshipEnd:
    return RelationshipEnd(
        class_id=ElementId(end_in.class_id),
        multiplicity=parse_multiplicity(end_in.multiplicity),
        role=end_in.role,
    )
