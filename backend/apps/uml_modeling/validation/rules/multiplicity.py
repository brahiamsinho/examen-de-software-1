"""Multiplicity range validation.

Ranges are checked here only — `Multiplicity` (`domain/types.py`) is a
deliberately unvalidated value object (DD2): if it rejected out-of-range
values at construction, this rule would be unreachable.
"""
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity
from apps.uml_modeling.validation.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    ElementKind,
    ElementRef,
    Severity,
    relationship_path,
)


def _is_invalid(multiplicity: Multiplicity) -> bool:
    if multiplicity.lower < 0:
        return True
    if multiplicity.upper is not None and multiplicity.upper < multiplicity.lower:
        return True
    return False


def invalid_multiplicity(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag every relationship with a negative lower bound, or an upper
    bound lower than its lower bound, on either endpoint.
    """
    diagnostics: list[Diagnostic] = []
    for relationship in model.relationships:
        if _is_invalid(relationship.source.multiplicity) or _is_invalid(
            relationship.target.multiplicity
        ):
            diagnostics.append(
                Diagnostic(
                    severity=Severity.ERROR,
                    code=DiagnosticCode.INVALID_MULTIPLICITY,
                    message=f"Relationship {relationship.id!r} has an invalid multiplicity",
                    path=relationship_path(relationship.id),
                    element_ref=ElementRef(kind=ElementKind.RELATIONSHIP, id=relationship.id),
                )
            )
    return tuple(diagnostics)
