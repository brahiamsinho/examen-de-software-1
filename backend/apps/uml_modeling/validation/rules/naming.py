"""Naming rules: empty names and duplicate names within their scope.

Each rule keeps the exact `(CanonicalUmlModel) -> Iterable[Diagnostic]`
signature (DD6) and builds its own local id-to-owner lookups rather than
relying on a shared prebuilt index, so it stays callable and testable in
isolation with zero setup.
"""
from apps.uml_modeling.domain.elements import Enumeration, EnumerationLiteral, UmlAttribute, UmlClass, UmlOperation
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.validation.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    ElementKind,
    ElementRef,
    Severity,
    attribute_path,
    class_path,
    enumeration_path,
    literal_path,
    operation_path,
)


def empty_element_name(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag every named element (class, attribute, operation,
    enumeration, literal) whose name is empty or whitespace-only.
    """
    attribute_owner: dict = {}
    operation_owner: dict = {}
    literal_owner: dict = {}
    for uml_class in model.classes:
        for attribute in uml_class.attributes:
            attribute_owner[attribute.id] = uml_class.id
        for operation in uml_class.operations:
            operation_owner[operation.id] = uml_class.id
    for enumeration in model.enumerations:
        for literal in enumeration.literals:
            literal_owner[literal.id] = enumeration.id

    diagnostics: list[Diagnostic] = []
    for element in model.iter_named_elements():
        if element.name.strip():
            continue

        if isinstance(element, UmlClass):
            path = class_path(element.id)
            ref = ElementRef(kind=ElementKind.CLASS, id=element.id)
        elif isinstance(element, UmlAttribute):
            path = attribute_path(attribute_owner[element.id], element.id)
            ref = ElementRef(kind=ElementKind.ATTRIBUTE, id=element.id)
        elif isinstance(element, UmlOperation):
            path = operation_path(operation_owner[element.id], element.id)
            ref = ElementRef(kind=ElementKind.OPERATION, id=element.id)
        elif isinstance(element, Enumeration):
            path = enumeration_path(element.id)
            ref = ElementRef(kind=ElementKind.ENUMERATION, id=element.id)
        elif isinstance(element, EnumerationLiteral):
            path = literal_path(literal_owner[element.id], element.id)
            ref = ElementRef(kind=ElementKind.LITERAL, id=element.id)
        else:  # pragma: no cover - iter_named_elements() has no other kind
            continue

        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                code=DiagnosticCode.EMPTY_ELEMENT_NAME,
                message="Element name must not be empty",
                path=path,
                element_ref=ref,
            )
        )
    return tuple(diagnostics)


def duplicate_class_name(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag every class after the first one sharing its name."""
    seen: set[str] = set()
    diagnostics: list[Diagnostic] = []
    for uml_class in model.classes:
        if uml_class.name in seen:
            diagnostics.append(
                Diagnostic(
                    severity=Severity.ERROR,
                    code=DiagnosticCode.DUPLICATE_CLASS_NAME,
                    message=f"Duplicate class name: {uml_class.name!r}",
                    path=class_path(uml_class.id),
                    element_ref=ElementRef(kind=ElementKind.CLASS, id=uml_class.id),
                )
            )
        else:
            seen.add(uml_class.name)
    return tuple(diagnostics)


def duplicate_attribute_name(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag every attribute after the first one sharing its name, scoped
    to its owning class.
    """
    diagnostics: list[Diagnostic] = []
    for uml_class in model.classes:
        seen: set[str] = set()
        for attribute in uml_class.attributes:
            if attribute.name in seen:
                diagnostics.append(
                    Diagnostic(
                        severity=Severity.ERROR,
                        code=DiagnosticCode.DUPLICATE_ATTRIBUTE_NAME,
                        message=f"Duplicate attribute name: {attribute.name!r}",
                        path=attribute_path(uml_class.id, attribute.id),
                        element_ref=ElementRef(kind=ElementKind.ATTRIBUTE, id=attribute.id),
                    )
                )
            else:
                seen.add(attribute.name)
    return tuple(diagnostics)


def duplicate_enumeration_literal(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag every literal after the first one sharing its name, scoped
    to its owning enumeration.
    """
    diagnostics: list[Diagnostic] = []
    for enumeration in model.enumerations:
        seen: set[str] = set()
        for literal in enumeration.literals:
            if literal.name in seen:
                diagnostics.append(
                    Diagnostic(
                        severity=Severity.ERROR,
                        code=DiagnosticCode.DUPLICATE_ENUMERATION_LITERAL,
                        message=f"Duplicate enumeration literal: {literal.name!r}",
                        path=literal_path(enumeration.id, literal.id),
                        element_ref=ElementRef(kind=ElementKind.LITERAL, id=literal.id),
                    )
                )
            else:
                seen.add(literal.name)
    return tuple(diagnostics)
