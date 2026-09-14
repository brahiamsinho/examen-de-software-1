"""Shared test factories for the uml_commands suites.

Wraps `apps.uml_modeling`'s own domain constructors so every uml_commands
test builds a minimal-but-valid document/model/relationship without
re-deriving the domain's field shapes in every test file (mirrors
`apps.uml_modeling.tests.factories`).
"""
import datetime
import uuid

from apps.uml_modeling.documents import DiagramLayout, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import Relationship, RelationshipEnd, RelationshipKind, UmlClass
from apps.uml_modeling.domain.ids import ElementId, new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity

_DEFAULT_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def a_class(
    *,
    name: str = "Order",
    attributes: tuple = (),
    operations: tuple = (),
    id: ElementId | None = None,
) -> UmlClass:
    return UmlClass(id=id or new_id(), name=name, attributes=attributes, operations=operations)


def a_relationship_end(
    *,
    class_id: ElementId | None = None,
    multiplicity: Multiplicity = Multiplicity(1, 1),
    role: str | None = None,
) -> RelationshipEnd:
    return RelationshipEnd(class_id=class_id or new_id(), multiplicity=multiplicity, role=role)


def a_relationship(
    *,
    kind: RelationshipKind = RelationshipKind.ASSOCIATION,
    source: RelationshipEnd | None = None,
    target: RelationshipEnd | None = None,
    id: ElementId | None = None,
) -> Relationship:
    return Relationship(
        id=id or new_id(),
        kind=kind,
        source=source or a_relationship_end(),
        target=target or a_relationship_end(),
    )


def a_document(
    *,
    model: CanonicalUmlModel | None = None,
    owner_id: str = "owner-1",
) -> ProjectDocument:
    return ProjectDocument(
        id=uuid.uuid4(),
        metadata=ProjectMetadata(name="My Project"),
        owner_id=owner_id,
        model=model if model is not None else CanonicalUmlModel(),
        layout=DiagramLayout(),
        created_at=_DEFAULT_TIMESTAMP,
        updated_at=_DEFAULT_TIMESTAMP,
    )
