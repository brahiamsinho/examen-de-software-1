"""UML structural elements: classes, enumerations, and relationships.

Cross-class links are expressed only through `Relationship` — an
attribute can never reference another `Class` directly, which is
enforced by `UmlAttribute.__post_init__` rejecting anything outside the
closed `AttributeType` union.
"""
from dataclasses import dataclass
from enum import StrEnum

from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.types import AttributeType, EnumerationRef, Multiplicity, PrimitiveType


class Visibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    PACKAGE = "package"


class RelationshipKind(StrEnum):
    ASSOCIATION = "association"
    AGGREGATION = "aggregation"
    COMPOSITION = "composition"
    GENERALIZATION = "generalization"


def _validate_attribute_type(type_value: object) -> None:
    if not isinstance(type_value, (PrimitiveType, EnumerationRef)):
        raise TypeError(
            "Attribute type must be a PrimitiveType or an EnumerationRef, "
            f"got {type_value!r}. Class-to-class links must be expressed "
            "as a Relationship, not an attribute type."
        )


@dataclass(frozen=True)
class UmlAttribute:
    id: ElementId
    name: str
    type: AttributeType
    visibility: Visibility = Visibility.PRIVATE

    def __post_init__(self) -> None:
        _validate_attribute_type(self.type)


@dataclass(frozen=True)
class UmlParameter:
    name: str
    type: AttributeType


@dataclass(frozen=True)
class UmlOperation:
    id: ElementId
    name: str
    return_type: AttributeType | None = None
    parameters: tuple[UmlParameter, ...] = ()
    visibility: Visibility = Visibility.PUBLIC


@dataclass(frozen=True)
class UmlClass:
    id: ElementId
    name: str
    attributes: tuple[UmlAttribute, ...] = ()
    operations: tuple[UmlOperation, ...] = ()
    visibility: Visibility = Visibility.PUBLIC


@dataclass(frozen=True)
class EnumerationLiteral:
    id: ElementId
    name: str
    value: str | None = None


@dataclass(frozen=True)
class Enumeration:
    id: ElementId
    name: str
    literals: tuple[EnumerationLiteral, ...] = ()


@dataclass(frozen=True)
class RelationshipEnd:
    class_id: ElementId
    multiplicity: Multiplicity
    role: str | None = None


@dataclass(frozen=True)
class Relationship:
    """A directed link between two classes.

    For `GENERALIZATION`, direction is normative: `source` is the
    specific (child) class, `target` is the general (parent) class.
    """

    id: ElementId
    kind: RelationshipKind
    source: RelationshipEnd
    target: RelationshipEnd
    name: str | None = None
