"""UML 2.5 `Class.isAbstract`: a class that is not meant to be instantiated."""
import dataclasses

from apps.uml_modeling.domain.elements import UmlClass
from apps.uml_modeling.domain.ids import new_id


def test_a_class_is_concrete_unless_it_says_otherwise():
    assert UmlClass(id=new_id(), name="Order").is_abstract is False


def test_a_class_can_be_abstract_and_the_flag_survives_a_copy():
    abstract = UmlClass(id=new_id(), name="Shape", is_abstract=True)

    assert dataclasses.replace(abstract, name="Figure").is_abstract is True


def test_the_flag_goes_after_the_existing_fields_so_positional_construction_still_works():
    # The XMI importer builds `UmlClass(id, name, attributes, operations, visibility)`.
    built = UmlClass(new_id(), "Order", (), (), UmlClass.__dataclass_fields__["visibility"].default)

    assert built.is_abstract is False
