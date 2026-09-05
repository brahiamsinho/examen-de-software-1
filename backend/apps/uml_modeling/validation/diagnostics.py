"""The diagnostic contract shared by every validation rule.

Path builders live here (DD9) rather than in a separate `paths.py`
because the `path` grammar is part of the diagnostic contract itself.
Every path is slash-rooted and id-based so it resolves unambiguously
to an element in the validated `CanonicalUmlModel`.
"""
from dataclasses import dataclass
from enum import StrEnum

from apps.uml_modeling.domain.ids import ElementId


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class DiagnosticCode(StrEnum):
    """The fixed, closed set of Cycle-1 diagnostic codes."""

    EMPTY_ELEMENT_NAME = "EMPTY_ELEMENT_NAME"
    DUPLICATE_CLASS_NAME = "DUPLICATE_CLASS_NAME"
    DUPLICATE_ATTRIBUTE_NAME = "DUPLICATE_ATTRIBUTE_NAME"
    DUPLICATE_ENUMERATION_LITERAL = "DUPLICATE_ENUMERATION_LITERAL"
    UNKNOWN_ATTRIBUTE_TYPE = "UNKNOWN_ATTRIBUTE_TYPE"
    INVALID_RELATIONSHIP_ENDPOINT = "INVALID_RELATIONSHIP_ENDPOINT"
    INVALID_MULTIPLICITY = "INVALID_MULTIPLICITY"
    GENERALIZATION_CYCLE = "GENERALIZATION_CYCLE"
    SELF_ASSOCIATION = "SELF_ASSOCIATION"
    CLASS_WITHOUT_ATTRIBUTES = "CLASS_WITHOUT_ATTRIBUTES"


class ElementKind(StrEnum):
    MODEL = "model"
    CLASS = "class"
    ATTRIBUTE = "attribute"
    OPERATION = "operation"
    ENUMERATION = "enumeration"
    LITERAL = "literal"
    RELATIONSHIP = "relationship"


@dataclass(frozen=True)
class ElementRef:
    kind: ElementKind
    id: ElementId


@dataclass(frozen=True)
class Diagnostic:
    severity: Severity
    code: DiagnosticCode
    message: str
    path: str
    element_ref: ElementRef | None = None


@dataclass(frozen=True)
class ValidationResult:
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.severity is Severity.ERROR)

    @property
    def is_blocking(self) -> bool:
        return bool(self.errors)


def class_path(class_id: ElementId) -> str:
    return f"/classes/{class_id}"


def attribute_path(class_id: ElementId, attribute_id: ElementId) -> str:
    return f"{class_path(class_id)}/attributes/{attribute_id}"


def operation_path(class_id: ElementId, operation_id: ElementId) -> str:
    return f"{class_path(class_id)}/operations/{operation_id}"


def enumeration_path(enumeration_id: ElementId) -> str:
    return f"/enumerations/{enumeration_id}"


def literal_path(enumeration_id: ElementId, literal_id: ElementId) -> str:
    return f"{enumeration_path(enumeration_id)}/literals/{literal_id}"


def relationship_path(relationship_id: ElementId) -> str:
    return f"/relationships/{relationship_id}"
