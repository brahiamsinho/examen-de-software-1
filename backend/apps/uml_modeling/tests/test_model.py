"""RED: apps.uml_modeling.domain.model does not exist yet."""
import dataclasses

from apps.uml_modeling.domain.elements import (
    Enumeration,
    EnumerationLiteral,
    UmlAttribute,
    UmlClass,
    UmlOperation,
)
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel, UmlModel
from apps.uml_modeling.domain.types import PrimitiveType


def test_uml_model_is_the_same_object_as_canonical_uml_model():
    assert UmlModel is CanonicalUmlModel


def test_model_preserves_declaration_order_of_classes_and_members():
    attribute_one = UmlAttribute(id=new_id(), name="id", type=PrimitiveType.STRING)
    attribute_two = UmlAttribute(id=new_id(), name="total", type=PrimitiveType.DECIMAL)
    operation_one = UmlOperation(id=new_id(), name="place")
    operation_two = UmlOperation(id=new_id(), name="cancel")
    order_class = UmlClass(
        id=new_id(),
        name="Order",
        attributes=(attribute_one, attribute_two),
        operations=(operation_one, operation_two),
    )
    customer_class = UmlClass(id=new_id(), name="Customer")

    model = CanonicalUmlModel(classes=(order_class, customer_class))

    assert model.classes == (order_class, customer_class)
    assert model.classes[0].attributes == (attribute_one, attribute_two)
    assert model.classes[0].operations == (operation_one, operation_two)


def test_class_by_id_finds_the_matching_class():
    order_class = UmlClass(id=new_id(), name="Order")
    customer_class = UmlClass(id=new_id(), name="Customer")
    model = CanonicalUmlModel(classes=(order_class, customer_class))

    assert model.class_by_id(customer_class.id) is customer_class


def test_class_by_id_returns_none_for_an_unknown_id():
    model = CanonicalUmlModel(classes=(UmlClass(id=new_id(), name="Order"),))

    assert model.class_by_id(new_id()) is None


def test_enumeration_by_id_finds_the_matching_enumeration():
    status = Enumeration(id=new_id(), name="OrderStatus")
    model = CanonicalUmlModel(enumerations=(status,))

    assert model.enumeration_by_id(status.id) is status


def test_iter_named_elements_walks_classes_attributes_operations_and_enumerations():
    attribute = UmlAttribute(id=new_id(), name="total", type=PrimitiveType.DECIMAL)
    operation = UmlOperation(id=new_id(), name="place")
    order_class = UmlClass(
        id=new_id(), name="Order", attributes=(attribute,), operations=(operation,)
    )
    literal = EnumerationLiteral(id=new_id(), name="DRAFT")
    status = Enumeration(id=new_id(), name="OrderStatus", literals=(literal,))
    model = CanonicalUmlModel(classes=(order_class,), enumerations=(status,))

    named_elements = list(model.iter_named_elements())

    assert order_class in named_elements
    assert attribute in named_elements
    assert operation in named_elements
    assert status in named_elements
    assert literal in named_elements


def test_generation_metadata_adds_no_field_to_elements():
    order_class = UmlClass(id=new_id(), name="Order")
    model = CanonicalUmlModel(
        classes=(order_class,),
        generation_metadata={order_class.id: {"source": "voice"}},
    )

    element_fields = {f.name for f in dataclasses.fields(model.classes[0])}

    assert "generation_metadata" not in element_fields
    assert model.generation_metadata[order_class.id] == {"source": "voice"}


def test_class_name_uniqueness_is_evaluated_at_model_root_with_no_package():
    first = UmlClass(id=new_id(), name="Order")
    second = UmlClass(id=new_id(), name="Order")
    model = CanonicalUmlModel(classes=(first, second))

    names = [uml_class.name for uml_class in model.classes]

    assert names.count("Order") == 2
    assert not hasattr(model, "packages")
