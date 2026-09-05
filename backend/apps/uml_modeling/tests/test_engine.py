"""RED: apps.uml_modeling.validation.engine does not exist yet."""
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.tests.factories import a_class, a_model
from apps.uml_modeling.validation.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    ElementKind,
    ElementRef,
    Severity,
)
from apps.uml_modeling.validation.engine import RULES, validate


def _fake_diagnostic(code: DiagnosticCode) -> Diagnostic:
    element_id = new_id()
    return Diagnostic(
        severity=Severity.ERROR,
        code=code,
        message="fake",
        path=f"/classes/{element_id}",
        element_ref=ElementRef(kind=ElementKind.CLASS, id=element_id),
    )


def test_valid_model_produces_no_errors_and_is_not_blocking():
    model = a_model(classes=(a_class(name="Order"),))

    result = validate(model, rules=())

    assert result.errors == ()
    assert result.is_blocking is False


def test_validate_never_short_circuits_and_aggregates_every_rule():
    first_diagnostic = _fake_diagnostic(DiagnosticCode.EMPTY_ELEMENT_NAME)
    second_diagnostic = _fake_diagnostic(DiagnosticCode.INVALID_MULTIPLICITY)

    def rule_one(model):
        return [first_diagnostic]

    def rule_two(model):
        return [second_diagnostic]

    result = validate(a_model(), rules=(rule_one, rule_two))

    assert result.diagnostics == (first_diagnostic, second_diagnostic)


def test_registry_has_exactly_ten_rules():
    assert len(RULES) == 10
