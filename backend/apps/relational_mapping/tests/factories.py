"""Test factories for `relational_mapping` mapper scenarios (design.md DD20).

Imports only `apps.uml_modeling.domain` — never the uml_modeling test
factories (`backend/apps/README.md` no-cross-imports convention).
Mapping scenarios need hierarchy/multiplicity-shaped builders the
validation factories do not provide.
"""
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
    id: ElementId | None = None,
) -> UmlClass:
    return UmlClass(id=id or new_id(), name=name, attributes=attributes)


def an_enumeration_literal(
    *, name: str = "DRAFT", value: str | None = None, id: ElementId | None = None
) -> EnumerationLiteral:
    return EnumerationLiteral(id=id or new_id(), name=name, value=value)


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
    source_role: str | None = None,
    target_role: str | None = None,
    id: ElementId | None = None,
) -> Relationship:
    return Relationship(
        id=id or new_id(),
        kind=kind,
        source=RelationshipEnd(
            class_id=source_id or new_id(), multiplicity=source_multiplicity, role=source_role
        ),
        target=RelationshipEnd(
            class_id=target_id or new_id(), multiplicity=target_multiplicity, role=target_role
        ),
    )


def a_generalization(
    *, source_id: ElementId, target_id: ElementId, id: ElementId | None = None
) -> Relationship:
    """child (source) generalizes to parent (target) — normative direction."""
    return a_relationship(
        kind=RelationshipKind.GENERALIZATION,
        source_id=source_id,
        target_id=target_id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(1, 1),
        id=id,
    )


def a_composition(
    *,
    whole_id: ElementId,
    part_id: ElementId,
    whole_multiplicity: Multiplicity = Multiplicity(1, 1),
    part_multiplicity: Multiplicity = Multiplicity(0, None),
    whole_role: str | None = None,
    part_role: str | None = None,
    id: ElementId | None = None,
) -> Relationship:
    """whole (source) owns part (target) — DD12 normative direction."""
    return a_relationship(
        kind=RelationshipKind.COMPOSITION,
        source_id=whole_id,
        target_id=part_id,
        source_multiplicity=whole_multiplicity,
        target_multiplicity=part_multiplicity,
        source_role=whole_role,
        target_role=part_role,
        id=id,
    )


def an_aggregation(
    *,
    whole_id: ElementId,
    part_id: ElementId,
    whole_multiplicity: Multiplicity = Multiplicity(1, 1),
    part_multiplicity: Multiplicity = Multiplicity(0, None),
    whole_role: str | None = None,
    part_role: str | None = None,
    id: ElementId | None = None,
) -> Relationship:
    return a_relationship(
        kind=RelationshipKind.AGGREGATION,
        source_id=whole_id,
        target_id=part_id,
        source_multiplicity=whole_multiplicity,
        target_multiplicity=part_multiplicity,
        source_role=whole_role,
        target_role=part_role,
        id=id,
    )


def an_association(
    *,
    source_id: ElementId,
    target_id: ElementId,
    source_multiplicity: Multiplicity = Multiplicity(1, 1),
    target_multiplicity: Multiplicity = Multiplicity(0, None),
    source_role: str | None = None,
    target_role: str | None = None,
    id: ElementId | None = None,
) -> Relationship:
    return a_relationship(
        kind=RelationshipKind.ASSOCIATION,
        source_id=source_id,
        target_id=target_id,
        source_multiplicity=source_multiplicity,
        target_multiplicity=target_multiplicity,
        source_role=source_role,
        target_role=target_role,
        id=id,
    )


def a_model(
    *,
    classes: tuple[UmlClass, ...] = (),
    enumerations: tuple[Enumeration, ...] = (),
    relationships: tuple[Relationship, ...] = (),
) -> CanonicalUmlModel:
    return CanonicalUmlModel(classes=classes, enumerations=enumerations, relationships=relationships)


def a_hierarchy(
    *, root_name: str = "Vehicle", child_name: str = "Car"
) -> tuple[UmlClass, UmlClass, Relationship]:
    """A minimal two-class Single Table generalization tree: `child`
    generalizes to `root` (child = source, root = target, DD6).
    """
    root = a_class(name=root_name)
    child = a_class(name=child_name)
    generalization = a_generalization(source_id=child.id, target_id=root.id)
    return root, child, generalization
