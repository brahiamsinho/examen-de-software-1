"""RED: mapper does not implement synthetic PK emission yet (Stage 3)."""
from apps.relational_mapping.domain.types import ColumnType
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import a_class, a_model


def test_every_table_has_exactly_one_uuid_primary_key():
    order = a_class(name="Order")
    model = a_model(classes=(order,))

    result = map_to_relational(model)

    table = result.table_by_name("order")
    assert table.primary_key.column_names == ("id",)
    assert table.primary_key.name == "pk_order"
    id_column = table.column_by_name("id")
    assert id_column.type is ColumnType.UUID
    assert id_column.nullable is False


def test_pk_is_independent_of_class_attributes():
    customer = a_class(name="Customer")
    order = a_class(name="Order")
    model = a_model(classes=(customer, order))

    result = map_to_relational(model)

    for table_name in ("customer", "order"):
        table = result.table_by_name(table_name)
        assert table.primary_key.column_names == ("id",)
        assert table.column_by_name("id").type is ColumnType.UUID
