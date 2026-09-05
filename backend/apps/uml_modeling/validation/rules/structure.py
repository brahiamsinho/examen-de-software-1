"""Structural quality rules that fall outside naming/type/relationship
concerns. `CLASS_WITHOUT_ATTRIBUTES` fits none of the other rule files,
hence its own module.
"""
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.validation.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    ElementKind,
    ElementRef,
    Severity,
    class_path,
)


def class_without_attributes(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag every class declaring zero attributes (WARNING, non-blocking)."""
    diagnostics: list[Diagnostic] = []
    for uml_class in model.classes:
        if uml_class.attributes:
            continue
        diagnostics.append(
            Diagnostic(
                severity=Severity.WARNING,
                code=DiagnosticCode.CLASS_WITHOUT_ATTRIBUTES,
                message=f"Class {uml_class.name!r} has no attributes",
                path=class_path(uml_class.id),
                element_ref=ElementRef(kind=ElementKind.CLASS, id=uml_class.id),
            )
        )
    return tuple(diagnostics)
