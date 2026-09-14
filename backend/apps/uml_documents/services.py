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

from django.http import Http404

from apps.organizations.models import Organization
from apps.uml_commands import commands
from apps.uml_commands.commands import UmlCommand
from apps.uml_commands.dispatcher import CommandResult, apply
from apps.uml_documents import codec, schemas
from apps.uml_documents.errors import InvalidCommandPayloadError
from apps.uml_documents.models import UmlDocument
from apps.uml_modeling.documents import DiagramLayout, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import (
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
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


def _get_row(*, organization: Organization, doc_id: UUID) -> UmlDocument:
    try:
        return UmlDocument.objects.for_organization(organization).get(id=doc_id)
    except UmlDocument.DoesNotExist as exc:
        raise Http404("Document not found") from exc


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


def submit_command(
    *, organization: Organization, doc_id: UUID, command: UmlCommand, now: datetime.datetime
) -> CommandResult:
    row = _get_row(organization=organization, doc_id=doc_id)
    document = _to_project_document(row)
    result = apply(document, command, now=now)
    _save(row, result.document)
    return result


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
