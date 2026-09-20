"""Sample UML model for the generated-project compile gate (design.md DD81).

Mirrors the slice-0 spike: it covers scalar types, an enumeration, a
many-to-one association, a Single Table hierarchy and an N:M join table, and
it goes through the real pipeline (`CanonicalUmlModel` -> `map_to_relational`).

Class ids are frozen uuid4-hex literals, the shape the editor produces via
`new_id()`. They are literals, not live `new_id()` calls, so the sample stays
byte-for-byte deterministic across processes (DD90). The hierarchy classes
(vehicle, car, truck) start with a digit on purpose: such an id is never a
legal Java identifier, so the compile gate proves that generated class names
come from the UML class names and never from the element ids.

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


_CUSTOMER_ID = "a3bb189e8bf94b3f9ab1c8f1d2e64a50"
_PURCHASE_ID = "c9bf9e5745154f4aa8a3b1f6d2e0c7d8"
_VEHICLE_ID = "1b4e28ba2fa14b2f8d5e6c1a9f3d7e01"
_CAR_ID = "7c9e6679742540de944be27a4a4b2c11"
_TRUCK_ID = "0f8fad5bd9cb469fa16570867728950e"
_PRODUCT_ID = "9d7e1c5a3b2f4e6d8a0b1c2d3e4f5a6b"
_TAG_ID = "f81d4fae7dec41d0a76500a0c91e6bf6"


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
        _class(_CUSTOMER_ID, "Customer", _attribute("fullName", PrimitiveType.STRING)),
        _class(
            _PURCHASE_ID,
            "Purchase",
            _attribute("total", PrimitiveType.DECIMAL),
            _attribute("status", EnumerationRef(status.id)),
            _attribute("placedAt", PrimitiveType.DATETIME),
            _attribute("gift", PrimitiveType.BOOLEAN),
            _attribute("itemCount", PrimitiveType.INTEGER),
            _attribute("notes", PrimitiveType.TEXT),
        ),
        _class(_VEHICLE_ID, "Vehicle", _attribute("plate", PrimitiveType.STRING)),
        _class(_CAR_ID, "Car", _attribute("doors", PrimitiveType.INTEGER)),
        _class(_TRUCK_ID, "Truck", _attribute("payload", PrimitiveType.DECIMAL)),
        _class(_PRODUCT_ID, "Product", _attribute("title", PrimitiveType.STRING)),
        _class(_TAG_ID, "Tag", _attribute("label", PrimitiveType.STRING)),
    )

    relationships = (
        # many-to-one: many Purchase rows point at one Customer.
        _relationship(
            "customer-purchases",
            RelationshipKind.ASSOCIATION,
            _end(_CUSTOMER_ID, 1, 1),
            _end(_PURCHASE_ID, 0, None),
        ),
        # Single Table hierarchy: child (source) generalizes to parent (target).
        _relationship(
            "car-is-vehicle",
            RelationshipKind.GENERALIZATION,
            _end(_CAR_ID, 1, 1),
            _end(_VEHICLE_ID, 1, 1),
        ),
        _relationship(
            "truck-is-vehicle",
            RelationshipKind.GENERALIZATION,
            _end(_TRUCK_ID, 1, 1),
            _end(_VEHICLE_ID, 1, 1),
        ),
        # N:M: both ends many -> join table.
        _relationship(
            "product-tags",
            RelationshipKind.ASSOCIATION,
            _end(_PRODUCT_ID, 0, None),
            _end(_TAG_ID, 0, None),
        ),
    )

    return CanonicalUmlModel(classes=classes, enumerations=(status,), relationships=relationships)


def build_sample_relational_model() -> RelationalModel:
    return map_to_relational(build_sample_model())
