"""RED: apps.uml_modeling.validation.diagnostics does not exist yet."""
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.validation.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    ElementKind,
    ElementRef,
    Severity,
    ValidationResult,
    attribute_path,
    class_path,
    enumeration_path,
    literal_path,
    operation_path,
    relationship_path,
)

TEN_CODES = {
    "EMPTY_ELEMENT_NAME",
    "DUPLICATE_CLASS_NAME",
    "DUPLICATE_ATTRIBUTE_NAME",
    "DUPLICATE_ENUMERATION_LITERAL",
    "UNKNOWN_ATTRIBUTE_TYPE",
    "INVALID_RELATIONSHIP_ENDPOINT",
    "INVALID_MULTIPLICITY",
    "GENERALIZATION_CYCLE",
    "SELF_ASSOCIATION",
    "CLASS_WITHOUT_ATTRIBUTES",
}


def test_diagnostic_code_has_exactly_the_ten_cycle_one_codes():
    assert {member.name for member in DiagnosticCode} == TEN_CODES


def test_severity_has_error_and_warning():
    assert {member.name for member in Severity} == {"ERROR", "WARNING"}


def test_element_kind_covers_every_named_element_kind():
    expected = {"MODEL", "CLASS", "ATTRIBUTE", "OPERATION", "ENUMERATION", "LITERAL", "RELATIONSHIP"}

    assert {member.name for member in ElementKind} == expected


def test_diagnostic_carries_all_required_fields():
    class_id = new_id()
    diagnostic = Diagnostic(
        severity=Severity.ERROR,
        code=DiagnosticCode.EMPTY_ELEMENT_NAME,
        message="Class name must not be empty",
        path=class_path(class_id),
        element_ref=ElementRef(kind=ElementKind.CLASS, id=class_id),
    )

    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.code is DiagnosticCode.EMPTY_ELEMENT_NAME
    assert diagnostic.path == f"/classes/{class_id}"
    assert diagnostic.element_ref == ElementRef(kind=ElementKind.CLASS, id=class_id)


def test_validation_result_errors_and_is_blocking_true_when_error_present():
    class_id = new_id()
    error = Diagnostic(
        severity=Severity.ERROR,
        code=DiagnosticCode.EMPTY_ELEMENT_NAME,
        message="empty",
        path=class_path(class_id),
        element_ref=ElementRef(kind=ElementKind.CLASS, id=class_id),
    )
    warning = Diagnostic(
        severity=Severity.WARNING,
        code=DiagnosticCode.CLASS_WITHOUT_ATTRIBUTES,
        message="no attributes",
        path=class_path(class_id),
        element_ref=ElementRef(kind=ElementKind.CLASS, id=class_id),
    )
    result = ValidationResult(diagnostics=(error, warning))

    assert result.errors == (error,)
    assert result.is_blocking is True


def test_validation_result_is_not_blocking_when_only_warnings_present():
    class_id = new_id()
    warning = Diagnostic(
        severity=Severity.WARNING,
        code=DiagnosticCode.CLASS_WITHOUT_ATTRIBUTES,
        message="no attributes",
        path=class_path(class_id),
        element_ref=ElementRef(kind=ElementKind.CLASS, id=class_id),
    )
    result = ValidationResult(diagnostics=(warning,))

    assert result.errors == ()
    assert result.is_blocking is False


def test_path_builders_produce_the_slash_rooted_grammar():
    class_id = new_id()
    attribute_id = new_id()
    operation_id = new_id()
    enumeration_id = new_id()
    literal_id = new_id()
    relationship_id = new_id()

    assert class_path(class_id) == f"/classes/{class_id}"
    assert attribute_path(class_id, attribute_id) == f"/classes/{class_id}/attributes/{attribute_id}"
    assert operation_path(class_id, operation_id) == f"/classes/{class_id}/operations/{operation_id}"
    assert enumeration_path(enumeration_id) == f"/enumerations/{enumeration_id}"
    assert literal_path(enumeration_id, literal_id) == (
        f"/enumerations/{enumeration_id}/literals/{literal_id}"
    )
    assert relationship_path(relationship_id) == f"/relationships/{relationship_id}"
