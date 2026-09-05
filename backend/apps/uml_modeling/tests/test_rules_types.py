"""RED: apps.uml_modeling.validation.rules.types does not exist yet."""
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.types import EnumerationRef, PrimitiveType
from apps.uml_modeling.tests.factories import a_class, an_attribute, an_enumeration, a_model
from apps.uml_modeling.validation.diagnostics import DiagnosticCode, ElementKind, Severity
from apps.uml_modeling.validation.rules.types import unknown_attribute_type


def test_unknown_attribute_type_flags_a_dangling_enumeration_ref():
    missing_id = new_id()
    attribute = an_attribute(name="status", type=EnumerationRef(enumeration_id=missing_id))
    owner = a_class(name="Order", attributes=(attribute,))
    model = a_model(classes=(owner,))

    diagnostics = unknown_attribute_type(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.UNKNOWN_ATTRIBUTE_TYPE
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/classes/{owner.id}/attributes/{attribute.id}"
    assert diagnostic.element_ref.kind is ElementKind.ATTRIBUTE
    assert diagnostic.element_ref.id == attribute.id


def test_unknown_attribute_type_accepts_a_resolvable_enumeration_ref():
    status = an_enumeration(name="Status")
    attribute = an_attribute(name="status", type=EnumerationRef(enumeration_id=status.id))
    owner = a_class(name="Order", attributes=(attribute,))
    model = a_model(classes=(owner,), enumerations=(status,))

    assert unknown_attribute_type(model) == ()


def test_unknown_attribute_type_accepts_a_primitive():
    attribute = an_attribute(name="total", type=PrimitiveType.DECIMAL)
    owner = a_class(name="Order", attributes=(attribute,))
    model = a_model(classes=(owner,))

    assert unknown_attribute_type(model) == ()
