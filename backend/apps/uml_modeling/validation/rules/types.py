"""Attribute type resolution rule.

Named `types.py` to match the `AttributeType` domain concept it
validates; absolute imports (Python 3 default) make the name collision
with the stdlib `types` module safe.
"""
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import EnumerationRef
from apps.uml_modeling.validation.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    ElementKind,
    ElementRef,
    Severity,
    attribute_path,
)


def unknown_attribute_type(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag every attribute typed `EnumerationRef` whose target
    enumeration id does not exist in the model.
    """
    known_enumeration_ids = {enumeration.id for enumeration in model.enumerations}

    diagnostics: list[Diagnostic] = []
    for uml_class in model.classes:
        for attribute in uml_class.attributes:
            if not isinstance(attribute.type, EnumerationRef):
                continue
            if attribute.type.enumeration_id in known_enumeration_ids:
                continue
            diagnostics.append(
                Diagnostic(
                    severity=Severity.ERROR,
                    code=DiagnosticCode.UNKNOWN_ATTRIBUTE_TYPE,
                    message=(
                        f"Attribute {attribute.name!r} references unknown "
                        f"enumeration id {attribute.type.enumeration_id!r}"
                    ),
                    path=attribute_path(uml_class.id, attribute.id),
                    element_ref=ElementRef(kind=ElementKind.ATTRIBUTE, id=attribute.id),
                )
            )
    return tuple(diagnostics)
