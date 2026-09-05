"""Shared test factories for the uml_modeling domain and validation suites.

Each factory builds a minimal-but-valid element/model so a test scenario
differs only in the single fact under test (e.g. a duplicate name, an
out-of-range multiplicity) — this is the main defence against the
validation rule scenarios becoming hand-built models in every test file.
"""
import datetime
import uuid

from apps.uml_modeling.documents import DiagramLayout, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import (
    Enumeration,
    EnumerationLiteral,
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlClass,
    Visibility,
)
from apps.uml_modeling.domain.ids import ElementId, new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import AttributeType, Multiplicity, PrimitiveType
from apps.uml_modeling.validation.diagnostics import Diagnostic, ElementKind

_DEFAULT_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def an_attribute(
    *,
    name: str = "field",
    type: AttributeType = PrimitiveType.STRING,
    visibility: Visibility = Visibility.PRIVATE,
    id: ElementId | None = None,
) -> UmlAttribute:
    return UmlAttribute(id=id or new_id(), name=name, type=type, visibility=visibility)


def a_class(
    *,
    name: str = "Order",
    attributes: tuple[UmlAttribute, ...] = (),
    operations: tuple = (),
    id: ElementId | None = None,
) -> UmlClass:
    return UmlClass(id=id or new_id(), name=name, attributes=attributes, operations=operations)


def an_enumeration_literal(*, name: str = "DRAFT", id: ElementId | None = None) -> EnumerationLiteral:
    return EnumerationLiteral(id=id or new_id(), name=name)


def an_enumeration(
    *,
    name: str = "OrderStatus",
    literals: tuple[EnumerationLiteral, ...] = (),
    id: ElementId | None = None,
) -> Enumeration:
    return Enumeration(id=id or new_id(), name=name, literals=literals)


def a_relationship(
    *,
    kind: RelationshipKind = RelationshipKind.ASSOCIATION,
    source_id: ElementId | None = None,
    target_id: ElementId | None = None,
    source_multiplicity: Multiplicity = Multiplicity(1, 1),
    target_multiplicity: Multiplicity = Multiplicity(0, None),
    id: ElementId | None = None,
) -> Relationship:
    return Relationship(
        id=id or new_id(),
        kind=kind,
        source=RelationshipEnd(class_id=source_id or new_id(), multiplicity=source_multiplicity),
        target=RelationshipEnd(class_id=target_id or new_id(), multiplicity=target_multiplicity),
    )


def a_model(
    *,
    classes: tuple[UmlClass, ...] = (),
    enumerations: tuple[Enumeration, ...] = (),
    relationships: tuple[Relationship, ...] = (),
) -> CanonicalUmlModel:
    return CanonicalUmlModel(classes=classes, enumerations=enumerations, relationships=relationships)


def diagnostic_resolves_to_a_real_element(model: CanonicalUmlModel, diagnostic: Diagnostic) -> bool:
    """Shared assertion helper (uml-validation REQ4 integration): a
    diagnostic's `element_ref` must resolve to an element actually
    present in the validated model.
    """
    ref = diagnostic.element_ref
    if ref is None:
        return False

    if ref.kind is ElementKind.CLASS:
        return model.class_by_id(ref.id) is not None
    if ref.kind is ElementKind.ENUMERATION:
        return model.enumeration_by_id(ref.id) is not None
    if ref.kind is ElementKind.ATTRIBUTE:
        return any(a.id == ref.id for c in model.classes for a in c.attributes)
    if ref.kind is ElementKind.OPERATION:
        return any(o.id == ref.id for c in model.classes for o in c.operations)
    if ref.kind is ElementKind.LITERAL:
        return any(l.id == ref.id for e in model.enumerations for l in e.literals)
    if ref.kind is ElementKind.RELATIONSHIP:
        return any(r.id == ref.id for r in model.relationships)
    return False


def a_project_document(
    *,
    name: str = "My Project",
    owner_id: str = "owner-1",
    model: CanonicalUmlModel | None = None,
    layout: DiagramLayout | None = None,
) -> ProjectDocument:
    return ProjectDocument(
        id=uuid.uuid4(),
        metadata=ProjectMetadata(name=name),
        owner_id=owner_id,
        model=model if model is not None else CanonicalUmlModel(),
        layout=layout if layout is not None else DiagramLayout(),
        created_at=_DEFAULT_TIMESTAMP,
        updated_at=_DEFAULT_TIMESTAMP,
    )
