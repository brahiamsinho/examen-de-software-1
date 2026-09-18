"""RED: mapper does not implement attribute->column mapping yet (Stage 3)."""
from apps.relational_mapping.domain.types import ColumnType
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import a_class, a_generalization, a_model, an_attribute
from apps.uml_modeling.domain.types import PrimitiveType

_PRIMITIVE_EXPECTATIONS = {
    PrimitiveType.STRING: {"type": ColumnType.VARCHAR, "length": 255},
    PrimitiveType.TEXT: {"type": ColumnType.TEXT},
    PrimitiveType.INTEGER: {"type": ColumnType.INTEGER},
    PrimitiveType.LONG: {"type": ColumnType.BIGINT},
    PrimitiveType.DECIMAL: {"type": ColumnType.NUMERIC, "precision": 19, "scale": 4},
    PrimitiveType.BOOLEAN: {"type": ColumnType.BOOLEAN},
    PrimitiveType.DATE: {"type": ColumnType.DATE},
    PrimitiveType.DATETIME: {"type": ColumnType.TIMESTAMPTZ},
}


def test_every_primitive_type_maps_to_its_column_type():
    for primitive_type, expectation in _PRIMITIVE_EXPECTATIONS.items():
        attribute = an_attribute(name="value", type=primitive_type)
        order_class = a_class(name="Order", attributes=(attribute,))
        model = a_model(classes=(order_class,))

        result = map_to_relational(model)

        column = result.table_by_name("order").column_by_name("value")
        assert column.type is expectation["type"], primitive_type
        assert column.length == expectation.get("length")
        assert column.precision == expectation.get("precision")
        assert column.scale == expectation.get("scale")


def test_root_attribute_column_is_not_null():
    attribute = an_attribute(name="total", type=PrimitiveType.DECIMAL)
    order_class = a_class(name="Order", attributes=(attribute,))
    model = a_model(classes=(order_class,))

    result = map_to_relational(model)

    column = result.table_by_name("order").column_by_name("total")
    assert column.nullable is False


def test_attribute_named_id_collides_with_synthetic_pk_and_gets_prefixed():
    attribute = an_attribute(name="id", type=PrimitiveType.STRING)
    order_class = a_class(name="Order", attributes=(attribute,))
    model = a_model(classes=(order_class,))

    result = map_to_relational(model)

    table = result.table_by_name("order")
    assert table.column_by_name("order_id") is not None
    assert table.column_by_name("order_id").source_element_id == attribute.id
    assert table.primary_key.column_names == ("id",)


def test_sibling_subclass_attribute_name_clash_is_disambiguated():
    root = a_class(name="Vehicle")
    car = a_class(name="Car", attributes=(an_attribute(name="color", type=PrimitiveType.STRING),))
    truck = a_class(name="Truck", attributes=(an_attribute(name="color", type=PrimitiveType.STRING),))
    car_generalizes = a_generalization(source_id=car.id, target_id=root.id)
    truck_generalizes = a_generalization(source_id=truck.id, target_id=root.id)
    model = a_model(classes=(root, car, truck), relationships=(car_generalizes, truck_generalizes))

    result = map_to_relational(model)

    table = result.table_by_name("vehicle")
    assert table.column_by_name("color") is not None
    assert table.column_by_name("truck_color") is not None


def test_attribute_named_class_type_is_disambiguated_from_discriminator():
    root = a_class(name="Vehicle")
    car = a_class(name="Car", attributes=(an_attribute(name="class_type", type=PrimitiveType.STRING),))
    generalization = a_generalization(source_id=car.id, target_id=root.id)
    model = a_model(classes=(root, car), relationships=(generalization,))

    result = map_to_relational(model)

    table = result.table_by_name("vehicle")
    assert table.discriminator_column == "class_type"
    assert table.column_by_name("car_class_type") is not None
