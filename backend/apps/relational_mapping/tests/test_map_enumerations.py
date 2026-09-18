"""RED: mapper does not implement enumeration mapping yet (Stage 2)."""
import pytest

from apps.relational_mapping.domain.types import ColumnType
from apps.relational_mapping.mapping.errors import UnknownEnumerationError
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import (
    a_class,
    a_model,
    an_attribute,
    an_enumeration,
    an_enumeration_literal,
)
from apps.uml_modeling.domain.types import EnumerationRef


def test_one_enum_type_per_enumeration_with_ordered_labels():
    enumeration = an_enumeration(
        name="OrderStatus",
        literals=(
            an_enumeration_literal(name="DRAFT"),
            an_enumeration_literal(name="PAID"),
        ),
    )
    model = a_model(enumerations=(enumeration,))

    result = map_to_relational(model)

    assert len(result.enum_types) == 1
    enum_type = result.enum_types[0]
    assert enum_type.name == "order_status"
    assert enum_type.labels == ("DRAFT", "PAID")
    assert enum_type.source_enumeration_id == enumeration.id


def test_literal_value_wins_over_name_for_labels():
    enumeration = an_enumeration(
        name="OrderStatus",
        literals=(an_enumeration_literal(name="DRAFT", value="borrador"),),
    )
    model = a_model(enumerations=(enumeration,))

    result = map_to_relational(model)

    assert result.enum_types[0].labels == ("borrador",)


def test_unreferenced_enumeration_is_still_emitted():
    enumeration = an_enumeration(name="Unused")
    model = a_model(enumerations=(enumeration,))

    result = map_to_relational(model)

    assert result.enum_type_by_name("unused") is not None


def test_attribute_referencing_enumeration_gets_enum_column():
    enumeration = an_enumeration(name="OrderStatus", literals=(an_enumeration_literal(name="DRAFT"),))
    status_attribute = an_attribute(name="status", type=EnumerationRef(enumeration.id))
    order_class = a_class(name="Order", attributes=(status_attribute,))
    model = a_model(classes=(order_class,), enumerations=(enumeration,))

    result = map_to_relational(model)

    table = result.table_by_name("order")
    column = table.column_by_name("status")
    assert column.type is ColumnType.ENUM
    assert column.enum_type_name == "order_status"


def test_unknown_enumeration_reference_raises():
    status_attribute = an_attribute(name="status", type=EnumerationRef("missing-enum-id"))
    order_class = a_class(name="Order", attributes=(status_attribute,))
    model = a_model(classes=(order_class,))

    with pytest.raises(UnknownEnumerationError) as excinfo:
        map_to_relational(model)

    assert excinfo.value.attribute_id == status_attribute.id
    assert excinfo.value.enumeration_id == "missing-enum-id"
