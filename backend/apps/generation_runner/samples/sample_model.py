"""Sample UML model for the generated-project compile gate (design.md DD81).

Mirrors the slice-0 spike: it covers scalar types, an enumeration, a
many-to-one association, a Single Table hierarchy and an N:M join table, and
it goes through the real pipeline (`CanonicalUmlModel` -> `map_to_relational`).

Element ids are READABLE strings ("customer", "vehicle", ...) on purpose.
Known defect, queued as a separate change:
`apps/spring_generator/emit/inheritance_context.py:169` renders
`pascal_case(class_id)` as the Java class name of every hierarchy subclass
where it must read `discriminator_values[class_id]`, so a uuid4 hex id yields
an invalid Java identifier. Once that line is fixed, switch these ids back to
`new_id()` and drop this workaround.

Glue code: this module may import the generator's inputs; nothing in the
pure `writer/` and `domain/` packages imports it (DD75).
"""
from apps.relational_mapping.domain.schema import RelationalModel
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.uml_modeling.domain.elements import (
    Enumeration,
    EnumerationLiteral,
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlClass,
)
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity, PrimitiveType


def _attribute(name: str, attribute_type) -> UmlAttribute:
    return UmlAttribute(id=ElementId(f"attribute-{name}"), name=name, type=attribute_type)


def _class(class_id: str, name: str, *attributes: UmlAttribute) -> UmlClass:
    return UmlClass(id=ElementId(class_id), name=name, attributes=attributes)


def _end(class_id: str, lower: int, upper: int | None, role: str | None = None) -> RelationshipEnd:
    return RelationshipEnd(class_id=ElementId(class_id), multiplicity=Multiplicity(lower, upper), role=role)


def _relationship(
    relationship_id: str, kind: RelationshipKind, source: RelationshipEnd, target: RelationshipEnd
) -> Relationship:
    return Relationship(id=ElementId(relationship_id), kind=kind, source=source, target=target)


def build_sample_model() -> CanonicalUmlModel:
    status = Enumeration(
        id=ElementId("purchase-status"),
        name="PurchaseStatus",
        literals=(
            EnumerationLiteral(id=ElementId("status-pending"), name="PENDING"),
            EnumerationLiteral(id=ElementId("status-paid"), name="PAID"),
            EnumerationLiteral(id=ElementId("status-shipped"), name="SHIPPED"),
        ),
    )

    classes = (
        _class("customer", "Customer", _attribute("fullName", PrimitiveType.STRING)),
        _class(
            "purchase",
            "Purchase",
            _attribute("total", PrimitiveType.DECIMAL),
            _attribute("status", EnumerationRef(status.id)),
            _attribute("placedAt", PrimitiveType.DATETIME),
            _attribute("gift", PrimitiveType.BOOLEAN),
            _attribute("itemCount", PrimitiveType.INTEGER),
            _attribute("notes", PrimitiveType.TEXT),
        ),
        _class("vehicle", "Vehicle", _attribute("plate", PrimitiveType.STRING)),
        _class("car", "Car", _attribute("doors", PrimitiveType.INTEGER)),
        _class("truck", "Truck", _attribute("payload", PrimitiveType.DECIMAL)),
        _class("product", "Product", _attribute("title", PrimitiveType.STRING)),
        _class("tag", "Tag", _attribute("label", PrimitiveType.STRING)),
    )

    relationships = (
        # many-to-one: many Purchase rows point at one Customer.
        _relationship(
            "customer-purchases",
            RelationshipKind.ASSOCIATION,
            _end("customer", 1, 1),
            _end("purchase", 0, None),
        ),
        # Single Table hierarchy: child (source) generalizes to parent (target).
        _relationship(
            "car-is-vehicle",
            RelationshipKind.GENERALIZATION,
            _end("car", 1, 1),
            _end("vehicle", 1, 1),
        ),
        _relationship(
            "truck-is-vehicle",
            RelationshipKind.GENERALIZATION,
            _end("truck", 1, 1),
            _end("vehicle", 1, 1),
        ),
        # N:M: both ends many -> join table.
        _relationship(
            "product-tags",
            RelationshipKind.ASSOCIATION,
            _end("product", 0, None),
            _end("tag", 0, None),
        ),
    )

    return CanonicalUmlModel(classes=classes, enumerations=(status,), relationships=relationships)


def build_sample_relational_model() -> RelationalModel:
    return map_to_relational(build_sample_model())
