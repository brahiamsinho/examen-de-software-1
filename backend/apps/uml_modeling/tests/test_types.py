"""RED: apps.uml_modeling.domain.types does not exist yet."""
import dataclasses

import pytest
from hypothesis import given
from hypothesis import strategies as st

from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.types import (
    AttributeType,
    EnumerationRef,
    Multiplicity,
    PrimitiveType,
    format_multiplicity,
    parse_multiplicity,
)


def test_all_eight_primitive_types_exist():
    expected = {
        "STRING",
        "TEXT",
        "INTEGER",
        "LONG",
        "DECIMAL",
        "BOOLEAN",
        "DATE",
        "DATETIME",
    }

    assert {member.name for member in PrimitiveType} == expected


def test_enumeration_ref_is_frozen():
    ref = EnumerationRef(enumeration_id=new_id())

    with pytest.raises(dataclasses.FrozenInstanceError):
        ref.enumeration_id = new_id()


def test_attribute_type_accepts_a_primitive():
    value: AttributeType = PrimitiveType.INTEGER

    assert value is PrimitiveType.INTEGER


def test_attribute_type_accepts_an_enumeration_ref():
    ref = EnumerationRef(enumeration_id=new_id())
    value: AttributeType = ref

    assert value is ref


def test_multiplicity_constructible_unvalidated():
    """Multiplicity MUST NOT validate its range at construction (DD2):
    range checking is the sole responsibility of the INVALID_MULTIPLICITY
    engine rule (Phase 7.4). If this raised here, that rule would be
    unreachable dead code.
    """
    negative_lower = Multiplicity(-1, None)
    upper_below_lower = Multiplicity(2, 1)

    assert negative_lower.lower == -1
    assert negative_lower.upper is None
    assert upper_below_lower.lower == 2
    assert upper_below_lower.upper == 1


def test_multiplicity_is_frozen():
    value = Multiplicity(0, 1)

    with pytest.raises(dataclasses.FrozenInstanceError):
        value.lower = 5


@given(st.sampled_from(["1", "0..1", "0..*", "1..*"]))
def test_format_of_parse_is_the_identity_for_every_uml_form(text):
    assert format_multiplicity(parse_multiplicity(text)) == text


@given(
    st.builds(
        Multiplicity,
        lower=st.integers(min_value=0, max_value=5),
        upper=st.one_of(st.none(), st.integers(min_value=0, max_value=5)),
    )
)
def test_parse_of_format_is_the_identity_for_every_multiplicity(value):
    assert parse_multiplicity(format_multiplicity(value)) == value


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1", Multiplicity(1, 1)),
        ("0..1", Multiplicity(0, 1)),
        ("0..*", Multiplicity(0, None)),
        ("1..*", Multiplicity(1, None)),
    ],
)
def test_parse_multiplicity_produces_the_expected_value(text, expected):
    assert parse_multiplicity(text) == expected


def test_parse_multiplicity_rejects_malformed_syntax():
    with pytest.raises(ValueError):
        parse_multiplicity("not-a-multiplicity")
