"""RED: apps.uml_modeling.validation.rules.naming does not exist yet.

Each rule is invoked directly (never through `validate`), asserting the
diagnostic's code, severity, path, and element_ref — per DD6, each rule
is callable and testable in isolation.
"""
from apps.uml_modeling.domain.elements import UmlOperation
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.tests.factories import a_class, an_attribute, an_enumeration, an_enumeration_literal, a_model
from apps.uml_modeling.validation.diagnostics import DiagnosticCode, ElementKind, Severity
from apps.uml_modeling.validation.rules.naming import (
    duplicate_attribute_name,
    duplicate_class_name,
    duplicate_enumeration_literal,
    duplicate_operation_name,
    empty_element_name,
)


def _an_operation(name: str) -> UmlOperation:
    return UmlOperation(id=new_id(), name=name)


def test_empty_element_name_flags_a_blank_class_name():
    blank_class = a_class(name="")
    model = a_model(classes=(blank_class,))

    diagnostics = empty_element_name(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.EMPTY_ELEMENT_NAME
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/classes/{blank_class.id}"
    assert diagnostic.element_ref.kind is ElementKind.CLASS
    assert diagnostic.element_ref.id == blank_class.id


def test_empty_element_name_flags_a_whitespace_only_class_name():
    whitespace_class = a_class(name="   ")
    model = a_model(classes=(whitespace_class,))

    diagnostics = empty_element_name(model)

    assert len(diagnostics) == 1
    assert diagnostics[0].element_ref.id == whitespace_class.id


def test_empty_element_name_flags_a_blank_attribute_name_with_class_scoped_path():
    blank_attribute = an_attribute(name="")
    owner = a_class(name="Order", attributes=(blank_attribute,))
    model = a_model(classes=(owner,))

    diagnostics = empty_element_name(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.EMPTY_ELEMENT_NAME
    assert diagnostic.path == f"/classes/{owner.id}/attributes/{blank_attribute.id}"
    assert diagnostic.element_ref.kind is ElementKind.ATTRIBUTE


def test_empty_element_name_flags_a_blank_operation_name_with_class_scoped_path():
    blank_operation = _an_operation("")
    owner = a_class(name="Order", operations=(blank_operation,))
    model = a_model(classes=(owner,))

    diagnostics = empty_element_name(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.EMPTY_ELEMENT_NAME
    assert diagnostic.path == f"/classes/{owner.id}/operations/{blank_operation.id}"
    assert diagnostic.element_ref.kind is ElementKind.OPERATION


def test_empty_element_name_produces_nothing_for_a_valid_model():
    model = a_model(classes=(a_class(name="Order"),))

    assert empty_element_name(model) == ()


def test_duplicate_class_name_flags_the_second_class_named_the_same():
    first = a_class(name="Order")
    second = a_class(name="Order")
    model = a_model(classes=(first, second))

    diagnostics = duplicate_class_name(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.DUPLICATE_CLASS_NAME
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/classes/{second.id}"
    assert diagnostic.element_ref == diagnostic.element_ref.__class__(kind=ElementKind.CLASS, id=second.id)


def test_duplicate_class_name_produces_nothing_for_unique_names():
    model = a_model(classes=(a_class(name="Order"), a_class(name="Customer")))

    assert duplicate_class_name(model) == ()


def test_duplicate_attribute_name_flags_the_second_attribute_named_the_same():
    first = an_attribute(name="total")
    second = an_attribute(name="total")
    owner = a_class(name="Order", attributes=(first, second))
    model = a_model(classes=(owner,))

    diagnostics = duplicate_attribute_name(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.DUPLICATE_ATTRIBUTE_NAME
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/classes/{owner.id}/attributes/{second.id}"


def test_duplicate_attribute_name_produces_nothing_for_unique_names():
    owner = a_class(name="Order", attributes=(an_attribute(name="id"), an_attribute(name="total")))
    model = a_model(classes=(owner,))

    assert duplicate_attribute_name(model) == ()


def test_duplicate_operation_name_flags_the_second_operation_named_the_same():
    first = _an_operation("crearUsuario")
    second = _an_operation("crearUsuario")
    owner = a_class(name="Order", operations=(first, second))
    model = a_model(classes=(owner,))

    diagnostics = duplicate_operation_name(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.DUPLICATE_OPERATION_NAME
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/classes/{owner.id}/operations/{second.id}"
    assert diagnostic.element_ref.kind is ElementKind.OPERATION


def test_duplicate_operation_name_ignores_return_type_differences():
    first = UmlOperation(id=new_id(), name="crearUsuario", return_type=None)
    second = UmlOperation(id=new_id(), name="crearUsuario", return_type=None)
    owner = a_class(name="Order", operations=(first, second))
    model = a_model(classes=(owner,))

    diagnostics = duplicate_operation_name(model)

    assert len(diagnostics) == 1


def test_duplicate_operation_name_produces_nothing_for_the_same_name_in_different_classes():
    class_a = a_class(name="A", operations=(_an_operation("crearUsuario"),))
    class_b = a_class(name="B", operations=(_an_operation("crearUsuario"),))
    model = a_model(classes=(class_a, class_b))

    assert duplicate_operation_name(model) == ()


def test_duplicate_operation_name_produces_nothing_for_unique_names():
    owner = a_class(name="Order", operations=(_an_operation("crear"), _an_operation("guardar")))
    model = a_model(classes=(owner,))

    assert duplicate_operation_name(model) == ()


def test_duplicate_enumeration_literal_flags_the_second_literal_named_the_same():
    first = an_enumeration_literal(name="ACTIVE")
    second = an_enumeration_literal(name="ACTIVE")
    owner = an_enumeration(name="Status", literals=(first, second))
    model = a_model(enumerations=(owner,))

    diagnostics = duplicate_enumeration_literal(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.DUPLICATE_ENUMERATION_LITERAL
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/enumerations/{owner.id}/literals/{second.id}"


def test_duplicate_enumeration_literal_produces_nothing_for_unique_names():
    owner = an_enumeration(
        name="Status", literals=(an_enumeration_literal(name="ACTIVE"), an_enumeration_literal(name="DONE"))
    )
    model = a_model(enumerations=(owner,))

    assert duplicate_enumeration_literal(model) == ()
