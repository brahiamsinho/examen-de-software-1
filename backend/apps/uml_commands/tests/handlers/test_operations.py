"""Unit tests for operation-level handlers: `add_operation`,
`remove_operation`.
"""
from apps.uml_modeling.domain.elements import UmlOperation
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import PrimitiveType
from apps.uml_commands.commands import AddOperation, RemoveOperation
from apps.uml_commands.handlers.operations import add_operation, remove_operation

from ..factories import a_class


def _an_operation(name: str) -> UmlOperation:
    return UmlOperation(id=new_id(), name=name, return_type=PrimitiveType.STRING)


def test_add_operation_appends_preserving_existing_order():
    first = _an_operation("first")
    second = _an_operation("second")
    original = a_class(operations=(first, second))
    model = CanonicalUmlModel(classes=(original,))
    new_operation = _an_operation("third")

    new_model = add_operation(model, AddOperation(class_id=original.id, operation=new_operation))

    updated = new_model.class_by_id(original.id)
    assert updated.operations == (first, second, new_operation)


def test_add_operation_unknown_class_id_is_a_no_op():
    model = CanonicalUmlModel(classes=(a_class(),))

    new_model = add_operation(model, AddOperation(class_id=new_id(), operation=_an_operation("op")))

    assert new_model is model


def test_remove_operation_removes_matching_preserving_order():
    first = _an_operation("first")
    second = _an_operation("second")
    third = _an_operation("third")
    original = a_class(operations=(first, second, third))
    model = CanonicalUmlModel(classes=(original,))

    new_model = remove_operation(model, RemoveOperation(class_id=original.id, operation_id=second.id))

    updated = new_model.class_by_id(original.id)
    assert updated.operations == (first, third)


def test_remove_operation_unknown_class_id_is_a_no_op():
    model = CanonicalUmlModel(classes=(a_class(),))

    new_model = remove_operation(model, RemoveOperation(class_id=new_id(), operation_id=new_id()))

    assert new_model is model


def test_remove_operation_unknown_operation_id_is_a_no_op():
    original = a_class(operations=(_an_operation("first"),))
    model = CanonicalUmlModel(classes=(original,))

    new_model = remove_operation(model, RemoveOperation(class_id=original.id, operation_id=new_id()))

    assert new_model is model
