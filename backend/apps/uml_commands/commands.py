"""The closed set of UML mutation commands (DD1).

Each command is its own frozen dataclass carrying already-constructed
domain value objects (DD3) rather than flattened constructor fields.
`UmlCommand` is a closed `Union` type alias, mirroring the project's own
closed-union convention (`domain/types.py::AttributeType`).
"""
from dataclasses import dataclass

from apps.uml_modeling.domain.elements import Relationship, UmlAttribute
from apps.uml_modeling.domain.ids import ElementId


@dataclass(frozen=True)
class AddClass:
    class_id: ElementId
    name: str


@dataclass(frozen=True)
class RemoveClass:
    class_id: ElementId


@dataclass(frozen=True)
class RenameClass:
    class_id: ElementId
    new_name: str


@dataclass(frozen=True)
class AddAttribute:
    class_id: ElementId
    attribute: UmlAttribute


@dataclass(frozen=True)
class RemoveAttribute:
    class_id: ElementId
    attribute_id: ElementId


@dataclass(frozen=True)
class AddRelationship:
    relationship: Relationship


@dataclass(frozen=True)
class RemoveRelationship:
    relationship_id: ElementId


UmlCommand = (
    AddClass
    | RemoveClass
    | RenameClass
    | AddAttribute
    | RemoveAttribute
    | AddRelationship
    | RemoveRelationship
)
