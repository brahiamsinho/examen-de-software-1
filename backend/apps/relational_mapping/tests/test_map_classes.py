"""RED: mapper does not implement class->table mapping yet (Stage 3)."""
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import a_class, a_model
from apps.uml_modeling.domain.model import CanonicalUmlModel


def test_simple_class_becomes_a_table():
    order_class = a_class(name="Order")
    model = a_model(classes=(order_class,))

    result = map_to_relational(model)

    assert len(result.tables) == 1
    assert result.tables[0].name == "order"


def test_table_name_is_snake_case_singular():
    order_line = a_class(name="OrderLine")
    model = a_model(classes=(order_line,))

    result = map_to_relational(model)

    assert result.table_by_name("order_line") is not None


def test_table_order_matches_model_classes_order():
    customer = a_class(name="Customer")
    order = a_class(name="Order")
    model = a_model(classes=(customer, order))

    result = map_to_relational(model)

    assert [table.name for table in result.tables] == ["customer", "order"]


def test_empty_model_maps_to_an_empty_relational_model():
    result = map_to_relational(CanonicalUmlModel())

    assert result.tables == ()
    assert result.enum_types == ()
