"""RED: apps.uml_modeling.validation.rules.structure does not exist yet."""
from apps.uml_modeling.tests.factories import a_class, an_attribute, a_model
from apps.uml_modeling.validation.diagnostics import DiagnosticCode, ElementKind, Severity
from apps.uml_modeling.validation.rules.structure import class_without_attributes


def test_class_without_attributes():
    empty_class = a_class(name="Marker")
    model = a_model(classes=(empty_class,))

    diagnostics = class_without_attributes(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.CLASS_WITHOUT_ATTRIBUTES
    assert diagnostic.severity is Severity.WARNING
    assert diagnostic.path == f"/classes/{empty_class.id}"
    assert diagnostic.element_ref.kind is ElementKind.CLASS
    assert diagnostic.element_ref.id == empty_class.id


def test_class_without_attributes_produces_nothing_when_a_class_has_attributes():
    populated_class = a_class(name="Order", attributes=(an_attribute(name="total"),))
    model = a_model(classes=(populated_class,))

    assert class_without_attributes(model) == ()
