"""Unit tests for attribute-level handlers: `add_attribute`,
`remove_attribute`.
"""
from apps.uml_modeling.domain.elements import UmlAttribute
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import PrimitiveType
from apps.uml_commands.commands import AddAttribute, RemoveAttribute
from apps.uml_commands.handlers.attributes import add_attribute, remove_attribute

from ..factories import a_class


def _an_attribute(name: str) -> UmlAttribute:
    return UmlAttribute(id=new_id(), name=name, type=PrimitiveType.STRING)


def test_add_attribute_appends_preserving_existing_order():
    first = _an_attribute("first")
    second = _an_attribute("second")
    original = a_class(attributes=(first, second))
    model = CanonicalUmlModel(classes=(original,))
    new_attribute = _an_attribute("third")

    new_model = add_attribute(model, AddAttribute(class_id=original.id, attribute=new_attribute))

    updated = new_model.class_by_id(original.id)
    assert updated.attributes == (first, second, new_attribute)


def test_add_attribute_unknown_class_id_is_a_no_op():
    model = CanonicalUmlModel(classes=(a_class(),))

    new_model = add_attribute(model, AddAttribute(class_id=new_id(), attribute=_an_attribute("field")))

    assert new_model is model


def test_remove_attribute_removes_matching_preserving_order():
    first = _an_attribute("first")
    second = _an_attribute("second")
    third = _an_attribute("third")
    original = a_class(attributes=(first, second, third))
    model = CanonicalUmlModel(classes=(original,))

    new_model = remove_attribute(model, RemoveAttribute(class_id=original.id, attribute_id=second.id))

    updated = new_model.class_by_id(original.id)
    assert updated.attributes == (first, third)


def test_remove_attribute_unknown_class_id_is_a_no_op():
    model = CanonicalUmlModel(classes=(a_class(),))

    new_model = remove_attribute(model, RemoveAttribute(class_id=new_id(), attribute_id=new_id()))

    assert new_model is model


def test_remove_attribute_unknown_attribute_id_is_a_no_op():
    original = a_class(attributes=(_an_attribute("first"),))
    model = CanonicalUmlModel(classes=(original,))

    new_model = remove_attribute(model, RemoveAttribute(class_id=original.id, attribute_id=new_id()))

    assert new_model is model
