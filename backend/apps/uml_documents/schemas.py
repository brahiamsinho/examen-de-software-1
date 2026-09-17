"""Ninja/Pydantic request and response schemas for the uml_documents
domain (design.md's Interfaces/Contracts block; DD2).

No ORM access here — `api.py` maps `services.py`-shaped dicts/dataclasses
onto these shapes, matching `apps.organizations.schemas`'s convention.
"""
from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from ninja import Schema
from pydantic import Field


class AddClassIn(Schema):
    type: Literal["AddClass"]
    class_id: str
    name: str


class RemoveClassIn(Schema):
    type: Literal["RemoveClass"]
    class_id: str


class RenameClassIn(Schema):
    type: Literal["RenameClass"]
    class_id: str
    new_name: str


class UmlAttributeIn(Schema):
    id: str
    name: str
    type: str | dict  # decoded the same way as codec._decode_attribute_type
    visibility: Literal["public", "private", "protected", "package"] = "private"


class AddAttributeIn(Schema):
    type: Literal["AddAttribute"]
    class_id: str
    attribute: UmlAttributeIn


class RemoveAttributeIn(Schema):
    type: Literal["RemoveAttribute"]
    class_id: str
    attribute_id: str


class UmlOperationIn(Schema):
    id: str
    name: str
    return_type: str | dict | None = None  # decoded via codec._decode_attribute_type
    visibility: Literal["public", "private", "protected", "package"] = "public"


class AddOperationIn(Schema):
    type: Literal["AddOperation"]
    class_id: str
    operation: UmlOperationIn


class RemoveOperationIn(Schema):
    type: Literal["RemoveOperation"]
    class_id: str
    operation_id: str


class RelationshipEndIn(Schema):
    class_id: str
    multiplicity: str  # e.g. "0..1", "1..*" — parsed via domain.types.parse_multiplicity
    role: str | None = None


class RelationshipIn(Schema):
    id: str
    kind: Literal["association", "aggregation", "composition", "generalization"]
    source: RelationshipEndIn
    target: RelationshipEndIn
    name: str | None = None


class AddRelationshipIn(Schema):
    type: Literal["AddRelationship"]
    relationship: RelationshipIn


class RemoveRelationshipIn(Schema):
    type: Literal["RemoveRelationship"]
    relationship_id: str


CommandIn = Annotated[
    Union[
        AddClassIn,
        RemoveClassIn,
        RenameClassIn,
        AddAttributeIn,
        RemoveAttributeIn,
        AddOperationIn,
        RemoveOperationIn,
        AddRelationshipIn,
        RemoveRelationshipIn,
    ],
    Field(discriminator="type"),
]


class DocumentCreateIn(Schema):
    name: str


class MetadataOut(Schema):
    name: str
    description: str


class DocumentOut(Schema):
    id: UUID
    owner_id: str
    revision: int
    metadata: MetadataOut
    model: dict  # raw codec._encode_model(...) output — no duplicated Pydantic shape
    layout: dict  # raw codec._encode_layout(...) output
    created_at: datetime
    updated_at: datetime


class DocumentSummaryOut(Schema):
    """Lightweight list-row shape (design.md DD2) — `name` is FLAT, not
    nested under `metadata` like `DocumentOut`. No `model`/`layout`: a
    list row never needs the full decoded diagram."""

    id: UUID
    name: str
    revision: int
    updated_at: datetime


class DiagnosticOut(Schema):
    severity: str
    code: str
    message: str
    path: str


class ValidationOut(Schema):
    is_valid: bool
    violations: list[DiagnosticOut]


class CommandResultOut(Schema):
    revision: int
    validation: ValidationOut
