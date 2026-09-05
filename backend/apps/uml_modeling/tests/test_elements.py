"""RED: apps.uml_modeling.domain.elements does not exist yet."""
import pytest

from apps.uml_modeling.domain.elements import (
    Enumeration,
    EnumerationLiteral,
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlClass,
    UmlOperation,
    UmlParameter,
    Visibility,
)
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity, PrimitiveType


def test_uml_attribute_accepts_a_primitive_type():
    attribute = UmlAttribute(id=new_id(), name="total", type=PrimitiveType.DECIMAL)

    assert attribute.type is PrimitiveType.DECIMAL


def test_uml_attribute_accepts_an_enumeration_ref_type():
    ref = EnumerationRef(enumeration_id=new_id())

    attribute = UmlAttribute(id=new_id(), name="status", type=ref)

    assert attribute.type is ref


def test_uml_attribute_rejects_a_class_id_typed_attribute():
    other_class_id = new_id()

    with pytest.raises(TypeError):
        UmlAttribute(id=new_id(), name="parent", type=other_class_id)


def test_uml_class_holds_attributes_and_operations_in_declaration_order():
    attribute_one = UmlAttribute(id=new_id(), name="id", type=PrimitiveType.STRING)
    attribute_two = UmlAttribute(id=new_id(), name="total", type=PrimitiveType.DECIMAL)
    operation = UmlOperation(id=new_id(), name="place")

    order = UmlClass(
        id=new_id(),
        name="Order",
        attributes=(attribute_one, attribute_two),
        operations=(operation,),
    )

    assert order.attributes == (attribute_one, attribute_two)
    assert order.operations == (operation,)


def test_uml_operation_default_visibility_is_public():
    operation = UmlOperation(id=new_id(), name="place")

    assert operation.visibility is Visibility.PUBLIC


def test_enumeration_holds_literals_in_declaration_order():
    draft = EnumerationLiteral(id=new_id(), name="DRAFT")
    sent = EnumerationLiteral(id=new_id(), name="SENT")

    status = Enumeration(id=new_id(), name="OrderStatus", literals=(draft, sent))

    assert status.literals == (draft, sent)


def test_relationship_declares_kind_and_endpoints_with_multiplicity():
    source_class_id = new_id()
    target_class_id = new_id()
    source = RelationshipEnd(class_id=source_class_id, multiplicity=Multiplicity(1, 1))
    target = RelationshipEnd(class_id=target_class_id, multiplicity=Multiplicity(0, None))

    relationship = Relationship(
        id=new_id(),
        kind=RelationshipKind.ASSOCIATION,
        source=source,
        target=target,
    )

    assert relationship.kind is RelationshipKind.ASSOCIATION
    assert relationship.source.class_id == source_class_id
    assert relationship.target.class_id == target_class_id


def test_uml_parameter_accepts_an_attribute_type():
    parameter = UmlParameter(name="amount", type=PrimitiveType.DECIMAL)

    assert parameter.type is PrimitiveType.DECIMAL
