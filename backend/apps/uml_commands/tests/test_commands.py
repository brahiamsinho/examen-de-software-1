"""Unit tests for the 11 `UmlCommand` dataclasses: each constructs with its
documented fields, each is frozen, and the `UmlCommand` union covers
exactly the 11 types.
"""
import dataclasses
import typing

import pytest

from apps.uml_modeling.domain.elements import (
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlOperation,
    Visibility,
)
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.types import Multiplicity, PrimitiveType
from apps.uml_commands.commands import (
    AddAttribute,
    AddClass,
    AddOperation,
    AddRelationship,
    RemoveAttribute,
    RemoveClass,
    RemoveOperation,
    RemoveRelationship,
    RenameClass,
    SetGenerationProfile,
    UmlCommand,
    UpdateRelationship,
)


def _an_attribute() -> UmlAttribute:
    return UmlAttribute(id=new_id(), name="field", type=PrimitiveType.STRING, visibility=Visibility.PRIVATE)


def _an_operation() -> UmlOperation:
    return UmlOperation(id=new_id(), name="crearUsuario", return_type=PrimitiveType.STRING, visibility=Visibility.PUBLIC)


def _a_relationship() -> Relationship:
    return Relationship(
        id=new_id(),
        kind=RelationshipKind.ASSOCIATION,
        source=RelationshipEnd(class_id=new_id(), multiplicity=Multiplicity(1, 1)),
        target=RelationshipEnd(class_id=new_id(), multiplicity=Multiplicity(0, None)),
    )


def test_add_class_constructs_with_documented_fields():
    class_id = new_id()

    command = AddClass(class_id=class_id, name="Order")

    assert command.class_id == class_id
    assert command.name == "Order"


def test_add_class_is_frozen():
    command = AddClass(class_id=new_id(), name="Order")

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.name = "Renamed"


def test_remove_class_constructs_with_documented_fields():
    class_id = new_id()

    command = RemoveClass(class_id=class_id)

    assert command.class_id == class_id


def test_remove_class_is_frozen():
    command = RemoveClass(class_id=new_id())

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.class_id = new_id()


def test_rename_class_constructs_with_documented_fields():
    class_id = new_id()

    command = RenameClass(class_id=class_id, new_name="Renamed")

    assert command.class_id == class_id
    assert command.new_name == "Renamed"


def test_rename_class_is_frozen():
    command = RenameClass(class_id=new_id(), new_name="Renamed")

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.new_name = "Other"


def test_add_attribute_constructs_with_documented_fields():
    class_id = new_id()
    attribute = _an_attribute()

    command = AddAttribute(class_id=class_id, attribute=attribute)

    assert command.class_id == class_id
    assert command.attribute is attribute


def test_add_attribute_is_frozen():
    command = AddAttribute(class_id=new_id(), attribute=_an_attribute())

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.attribute = _an_attribute()


def test_remove_attribute_constructs_with_documented_fields():
    class_id = new_id()
    attribute_id = new_id()

    command = RemoveAttribute(class_id=class_id, attribute_id=attribute_id)

    assert command.class_id == class_id
    assert command.attribute_id == attribute_id


def test_remove_attribute_is_frozen():
    command = RemoveAttribute(class_id=new_id(), attribute_id=new_id())

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.attribute_id = new_id()


def test_add_operation_constructs_with_documented_fields():
    class_id = new_id()
    operation = _an_operation()

    command = AddOperation(class_id=class_id, operation=operation)

    assert command.class_id == class_id
    assert command.operation is operation


def test_add_operation_is_frozen():
    command = AddOperation(class_id=new_id(), operation=_an_operation())

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.operation = _an_operation()


def test_remove_operation_constructs_with_documented_fields():
    class_id = new_id()
    operation_id = new_id()

    command = RemoveOperation(class_id=class_id, operation_id=operation_id)

    assert command.class_id == class_id
    assert command.operation_id == operation_id


def test_remove_operation_is_frozen():
    command = RemoveOperation(class_id=new_id(), operation_id=new_id())

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.operation_id = new_id()


def test_add_relationship_constructs_with_documented_fields():
    relationship = _a_relationship()

    command = AddRelationship(relationship=relationship)

    assert command.relationship is relationship


def test_add_relationship_is_frozen():
    command = AddRelationship(relationship=_a_relationship())

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.relationship = _a_relationship()


def test_remove_relationship_constructs_with_documented_fields():
    relationship_id = new_id()

    command = RemoveRelationship(relationship_id=relationship_id)

    assert command.relationship_id == relationship_id


def test_remove_relationship_is_frozen():
    command = RemoveRelationship(relationship_id=new_id())

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.relationship_id = new_id()


def test_uml_command_union_covers_exactly_the_eleven_types():
    members = set(typing.get_args(UmlCommand))

    assert members == {
        AddClass,
        RemoveClass,
        RenameClass,
        AddAttribute,
        RemoveAttribute,
        AddOperation,
        RemoveOperation,
        AddRelationship,
        RemoveRelationship,
        UpdateRelationship,
        SetGenerationProfile,
    }


def test_set_generation_profile_constructs_with_element_id_and_profile():
    element_id = new_id()
    profile = {"entity": True, "crud": ["create", "read"]}

    command = SetGenerationProfile(element_id=element_id, profile=profile)

    assert command.element_id == element_id
    assert command.profile == profile


def test_set_generation_profile_profile_defaults_to_none():
    command = SetGenerationProfile(element_id=new_id())

    assert command.profile is None


def test_set_generation_profile_is_frozen():
    command = SetGenerationProfile(element_id=new_id())

    with pytest.raises(dataclasses.FrozenInstanceError):
        command.profile = {"entity": True}
