"""ProjectDocument: the persistence envelope wrapping a CanonicalUmlModel.

Splits semantic content (`CanonicalUmlModel`) from visual-only content
(`DiagramLayout`) so moving a shape on the canvas never touches the
model, and vice versa. `owner_id` is a deliberately opaque `str`: this
module MUST NOT import `django.contrib.auth` or any auth module — it
never interprets, resolves, or authorizes the owner identity.
"""
import datetime
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from uuid import UUID

from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel


@dataclass(frozen=True)
class ProjectMetadata:
    name: str
    description: str = ""


@dataclass(frozen=True)
class Position:
    x: float
    y: float


@dataclass(frozen=True)
class DiagramLayout:
    positions: Mapping[ElementId, Position] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDocument:
    id: UUID
    metadata: ProjectMetadata
    owner_id: str
    model: CanonicalUmlModel
    layout: DiagramLayout
    created_at: datetime.datetime
    updated_at: datetime.datetime
    revision: int = 1

    def __post_init__(self) -> None:
        if not self.owner_id:
            raise ValueError("ProjectDocument.owner_id must be a non-empty string")

    def with_model(self, model: CanonicalUmlModel, *, now: datetime.datetime) -> "ProjectDocument":
        """Return a copy with a new `UmlModel`; `layout` is untouched."""
        return replace(self, model=model, revision=self.revision + 1, updated_at=now)

    def with_layout(self, layout: DiagramLayout, *, now: datetime.datetime) -> "ProjectDocument":
        """Return a copy with a new `DiagramLayout`; `model` is untouched."""
        return replace(self, layout=layout, revision=self.revision + 1, updated_at=now)
