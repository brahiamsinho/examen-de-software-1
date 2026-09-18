"""RED: mapper does not implement Single Table inheritance collapse yet (Stage 3)."""
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import a_class, a_generalization, a_model, an_attribute
from apps.uml_modeling.domain.types import PrimitiveType


def test_subclass_columns_merge_into_the_root_table():
    vehicle = a_class(name="Vehicle", attributes=(an_attribute(name="brand", type=PrimitiveType.STRING),))
    car = a_class(name="Car", attributes=(an_attribute(name="doors", type=PrimitiveType.INTEGER),))
    generalization = a_generalization(source_id=car.id, target_id=vehicle.id)
    model = a_model(classes=(vehicle, car), relationships=(generalization,))

    result = map_to_relational(model)

    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.name == "vehicle"
    assert table.column_by_name("brand") is not None
    assert table.column_by_name("doors") is not None
    assert result.table_by_name("car") is None


def test_discriminator_column_has_verbatim_class_name_values():
    vehicle = a_class(name="Vehicle")
    car = a_class(name="Car")
    generalization = a_generalization(source_id=car.id, target_id=vehicle.id)
    model = a_model(classes=(vehicle, car), relationships=(generalization,))

    result = map_to_relational(model)

    table = result.tables[0]
    assert table.discriminator_column == "class_type"
    assert table.discriminator_values[vehicle.id] == "Vehicle"
    assert table.discriminator_values[car.id] == "Car"


def test_descendant_columns_are_nullable_root_columns_are_not():
    vehicle = a_class(name="Vehicle", attributes=(an_attribute(name="brand", type=PrimitiveType.STRING),))
    car = a_class(name="Car", attributes=(an_attribute(name="doors", type=PrimitiveType.INTEGER),))
    generalization = a_generalization(source_id=car.id, target_id=vehicle.id)
    model = a_model(classes=(vehicle, car), relationships=(generalization,))

    result = map_to_relational(model)

    table = result.tables[0]
    assert table.column_by_name("brand").nullable is False
    assert table.column_by_name("doors").nullable is True


def test_single_class_has_no_discriminator():
    order = a_class(name="Order")
    model = a_model(classes=(order,))

    result = map_to_relational(model)

    table = result.tables[0]
    assert table.discriminator_column is None
    assert dict(table.discriminator_values) == {}
