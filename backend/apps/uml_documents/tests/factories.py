"""Shared test factories for the uml_documents suites.

Wraps `apps.uml_modeling`'s own domain constructors so codec, services,
and integration tests all build a non-trivial fixture (multi-class,
multi-enumeration, multi-relationship, non-empty `generation_metadata`,
non-empty `positions`) without re-deriving the domain's field shapes in
every test file (mirrors `apps.uml_commands.tests.factories`).
"""
from apps.uml_modeling.documents import DiagramLayout, Position, ProjectMetadata
from apps.uml_modeling.domain.elements import (
    Enumeration,
    EnumerationLiteral,
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlClass,
)
from apps.uml_modeling.domain.ids import ElementId, new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity, PrimitiveType


def a_metadata(*, name: str = "My Diagram", description: str = "") -> ProjectMetadata:
    return ProjectMetadata(name=name, description=description)


def a_model() -> CanonicalUmlModel:
    """A non-trivial fixture: multiple classes, an enumeration, a
    relationship, and non-empty `generation_metadata` — both
    `AttributeType` branches (`PrimitiveType` and `EnumerationRef`) are
    exercised across the two classes' attributes.
    """
    status_enum_id = new_id()
    status_enum = Enumeration(
        id=status_enum_id,
        name="Status",
        literals=(
            EnumerationLiteral(id=new_id(), name="ACTIVE", value="active"),
            EnumerationLiteral(id=new_id(), name="INACTIVE", value="inactive"),
        ),
    )

    order_class_id = new_id()
    order_class = UmlClass(
        id=order_class_id,
        name="Order",
        attributes=(
            UmlAttribute(id=new_id(), name="reference", type=PrimitiveType.STRING),
            UmlAttribute(
                id=new_id(), name="status", type=EnumerationRef(enumeration_id=status_enum_id)
            ),
        ),
    )

    customer_class_id = new_id()
    customer_class = UmlClass(
        id=customer_class_id,
        name="Customer",
        attributes=(UmlAttribute(id=new_id(), name="name", type=PrimitiveType.STRING),),
    )

    relationship = Relationship(
        id=new_id(),
        kind=RelationshipKind.ASSOCIATION,
        source=RelationshipEnd(class_id=order_class_id, multiplicity=Multiplicity(1, 1)),
        target=RelationshipEnd(class_id=customer_class_id, multiplicity=Multiplicity(0, None)),
        name="placed_by",
    )

    return CanonicalUmlModel(
        classes=(order_class, customer_class),
        enumerations=(status_enum,),
        relationships=(relationship,),
        generation_metadata={
            order_class_id: {"source": "manual", "confidence": 1.0},
            customer_class_id: {"source": "voice", "confidence": 0.87},
        },
    )


def a_layout(model: CanonicalUmlModel | None = None) -> DiagramLayout:
    """A non-empty `positions` mapping keyed by every class in `model`
    (or two synthetic ids when no model is supplied).
    """
    if model is not None and model.classes:
        class_ids = [uml_class.id for uml_class in model.classes]
    else:
        class_ids = [new_id(), new_id()]

    return DiagramLayout(
        positions={
            class_id: Position(x=float(index) * 120.0, y=float(index) * 80.0)
            for index, class_id in enumerate(class_ids)
        }
    )
