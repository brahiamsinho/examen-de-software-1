"""JSON codec for the `ProjectDocument` content triple (metadata, model,
layout) — design.md DD5, DD6, DD7.

Operates only on the content triple, never on the whole `ProjectDocument`:
the persisted `data` blob never carries `id`/`owner_id`/`revision` (those
are real `UmlDocument` columns, per DD3). `services.py` is the sole place
that reassembles a full `ProjectDocument` from row columns + this decoded
triple.
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
    UmlOperation,
    UmlParameter,
    Visibility,
)
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import AttributeType, EnumerationRef, Multiplicity, PrimitiveType


def to_json(metadata: ProjectMetadata, model: CanonicalUmlModel, layout: DiagramLayout) -> dict:
    return {
        "metadata": _encode_metadata(metadata),
        "model": _encode_model(model),
        "layout": _encode_layout(layout),
    }


def from_json(data: dict) -> tuple[ProjectMetadata, CanonicalUmlModel, DiagramLayout]:
    return (
        _decode_metadata(data["metadata"]),
        _decode_model(data["model"]),
        _decode_layout(data["layout"]),
    )


def document_out(document) -> dict:
    """The wire shape of a full `ProjectDocument` (design.md DD6) —
    promoted from `api._document_out`, composed from the existing
    `_encode_model`/`_encode_layout`. Reused verbatim as the WS broadcast
    payload (DD7), so a broadcast and a `GET .../documents/{docId}` stay
    byte-identical by construction.
    """
    return {
        "id": document.id,
        "owner_id": document.owner_id,
        "revision": document.revision,
        "metadata": {"name": document.metadata.name, "description": document.metadata.description},
        "model": _encode_model(document.model),
        "layout": _encode_layout(document.layout),
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


# --- metadata --------------------------------------------------------------

def _encode_metadata(metadata: ProjectMetadata) -> dict:
    return {"name": metadata.name, "description": metadata.description}


def _decode_metadata(data: dict) -> ProjectMetadata:
    return ProjectMetadata(name=data["name"], description=data["description"])


# --- model -------------------------------------------------------------------

def _encode_model(model: CanonicalUmlModel) -> dict:
    return {
        "classes": [_encode_class(c) for c in model.classes],
        "enumerations": [_encode_enumeration(e) for e in model.enumerations],
        "relationships": [_encode_relationship(r) for r in model.relationships],
        "generation_metadata": {k: v for k, v in model.generation_metadata.items()},
    }


def _decode_model(data: dict) -> CanonicalUmlModel:
    return CanonicalUmlModel(
        classes=tuple(_decode_class(c) for c in data["classes"]),
        enumerations=tuple(_decode_enumeration(e) for e in data["enumerations"]),
        relationships=tuple(_decode_relationship(r) for r in data["relationships"]),
        generation_metadata={ElementId(k): v for k, v in data["generation_metadata"].items()},
    )


# --- classes -----------------------------------------------------------------

def _encode_class(uml_class: UmlClass) -> dict:
    return {
        "id": uml_class.id,
        "name": uml_class.name,
        "visibility": uml_class.visibility.value,
        "attributes": [_encode_attribute(a) for a in uml_class.attributes],
        "operations": [_encode_operation(o) for o in uml_class.operations],
    }


def _decode_class(data: dict) -> UmlClass:
    return UmlClass(
        id=ElementId(data["id"]),
        name=data["name"],
        visibility=Visibility(data["visibility"]),
        attributes=tuple(_decode_attribute(a) for a in data["attributes"]),
        operations=tuple(_decode_operation(o) for o in data["operations"]),
    )


def _encode_attribute(attribute: UmlAttribute) -> dict:
    return {
        "id": attribute.id,
        "name": attribute.name,
        "type": _encode_attribute_type(attribute.type),
        "visibility": attribute.visibility.value,
    }


def _decode_attribute(data: dict) -> UmlAttribute:
    return UmlAttribute(
        id=ElementId(data["id"]),
        name=data["name"],
        type=_decode_attribute_type(data["type"]),
        visibility=Visibility(data["visibility"]),
    )


def _encode_operation(operation: UmlOperation) -> dict:
    return {
        "id": operation.id,
        "name": operation.name,
        "return_type": _encode_attribute_type(operation.return_type)
        if operation.return_type is not None
        else None,
        "parameters": [_encode_parameter(p) for p in operation.parameters],
        "visibility": operation.visibility.value,
    }


def _decode_operation(data: dict) -> UmlOperation:
    return UmlOperation(
        id=ElementId(data["id"]),
        name=data["name"],
        return_type=_decode_attribute_type(data["return_type"])
        if data["return_type"] is not None
        else None,
        parameters=tuple(_decode_parameter(p) for p in data["parameters"]),
        visibility=Visibility(data["visibility"]),
    )


def _encode_parameter(parameter: UmlParameter) -> dict:
    return {"name": parameter.name, "type": _encode_attribute_type(parameter.type)}


def _decode_parameter(data: dict) -> UmlParameter:
    return UmlParameter(name=data["name"], type=_decode_attribute_type(data["type"]))


# --- enumerations --------------------------------------------------------------

def _encode_enumeration(enumeration: Enumeration) -> dict:
    return {
        "id": enumeration.id,
        "name": enumeration.name,
        "literals": [_encode_literal(literal) for literal in enumeration.literals],
    }


def _decode_enumeration(data: dict) -> Enumeration:
    return Enumeration(
        id=ElementId(data["id"]),
        name=data["name"],
        literals=tuple(_decode_literal(literal) for literal in data["literals"]),
    )


def _encode_literal(literal: EnumerationLiteral) -> dict:
    return {"id": literal.id, "name": literal.name, "value": literal.value}


def _decode_literal(data: dict) -> EnumerationLiteral:
    return EnumerationLiteral(id=ElementId(data["id"]), name=data["name"], value=data["value"])


# --- relationships --------------------------------------------------------------

def _encode_relationship(relationship: Relationship) -> dict:
    return {
        "id": relationship.id,
        "kind": relationship.kind.value,
        "source": _encode_relationship_end(relationship.source),
        "target": _encode_relationship_end(relationship.target),
        "name": relationship.name,
    }


def _decode_relationship(data: dict) -> Relationship:
    return Relationship(
        id=ElementId(data["id"]),
        kind=RelationshipKind(data["kind"]),
        source=_decode_relationship_end(data["source"]),
        target=_decode_relationship_end(data["target"]),
        name=data["name"],
    )


def _encode_relationship_end(end: RelationshipEnd) -> dict:
    return {
        "class_id": end.class_id,
        "multiplicity": _encode_multiplicity(end.multiplicity),
        "role": end.role,
    }


def _decode_relationship_end(data: dict) -> RelationshipEnd:
    return RelationshipEnd(
        class_id=ElementId(data["class_id"]),
        multiplicity=_decode_multiplicity(data["multiplicity"]),
        role=data["role"],
    )


def _encode_multiplicity(multiplicity: Multiplicity) -> dict:
    return {"lower": multiplicity.lower, "upper": multiplicity.upper}


def _decode_multiplicity(data: dict) -> Multiplicity:
    return Multiplicity(lower=data["lower"], upper=data["upper"])


# --- attribute type (closed union) --------------------------------------------

def _encode_attribute_type(value: AttributeType) -> str | dict:
    if isinstance(value, EnumerationRef):
        return {"enumeration_ref": {"enumeration_id": str(value.enumeration_id)}}
    return value.value  # PrimitiveType is a StrEnum


def _decode_attribute_type(value: str | dict) -> AttributeType:
    if isinstance(value, str):
        return PrimitiveType(value)
    return EnumerationRef(enumeration_id=ElementId(value["enumeration_ref"]["enumeration_id"]))


# --- layout --------------------------------------------------------------------

def _encode_layout(layout: DiagramLayout) -> dict:
    return {"positions": {k: {"x": p.x, "y": p.y} for k, p in layout.positions.items()}}


def _decode_layout(data: dict) -> DiagramLayout:
    return DiagramLayout(
        positions={ElementId(k): Position(x=v["x"], y=v["y"]) for k, v in data["positions"].items()}
    )
