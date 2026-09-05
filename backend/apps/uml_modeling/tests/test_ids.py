"""RED: apps.uml_modeling.domain.ids does not exist yet."""
from apps.uml_modeling.domain.ids import ElementId, new_id


def test_new_id_returns_a_hex_string():
    identifier = new_id()

    assert isinstance(identifier, str)
    assert len(identifier) == 32
    assert all(char in "0123456789abcdef" for char in identifier)


def test_new_id_returns_a_different_value_each_call():
    first = new_id()
    second = new_id()

    assert first != second


def test_element_id_type_annotation_accepts_a_str_value():
    value: ElementId = ElementId("abc123")

    assert value == "abc123"
