from apps.relational_mapping.domain.schema import Column, ForeignKey, PrimaryKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.inheritance_context import build_inheritance_hierarchy_context
from apps.spring_generator.tests.factories import a_column


def _vehicle_table() -> Table:
    garage_fk = ForeignKey(
        name="fk_vehicle__garage_id",
        column_names=("garage_id",),
        referenced_table="garage",
        referenced_column_names=("id",),
    )
    return Table(
        name="vehicle",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name="class_type", type=ColumnType.VARCHAR, nullable=False),
            a_column(name="vin", type=ColumnType.VARCHAR, nullable=False, length=17, owning_class_id="vehicle"),
            a_column(name="garage_id", type=ColumnType.UUID, nullable=True),
            a_column(name="fuel", type=ColumnType.ENUM, nullable=False, enum_type_name="fuel_type", owning_class_id="vehicle"),
            a_column(name="door_count", type=ColumnType.INTEGER, nullable=True, owning_class_id="car"),
            a_column(name="trim", type=ColumnType.ENUM, nullable=True, enum_type_name="trim_level", owning_class_id="car"),
            a_column(name="payload_capacity", type=ColumnType.NUMERIC, nullable=True, precision=10, scale=2, owning_class_id="pickup_truck"),
            a_column(name="axle_count", type=ColumnType.INTEGER, nullable=True, owning_class_id="truck"),
        ),
        primary_key=PrimaryKey(column_names=("id",), name="pk_vehicle"),
        foreign_keys=(garage_fk,),
        source_class_ids=("vehicle", "car", "pickup_truck", "truck"),
        discriminator_column="class_type",
        discriminator_values={
            "vehicle": "VEHICLE",
            "car": "CAR",
            "pickup_truck": "PICKUP_TRUCK",
            "truck": "TRUCK",
        },
    )


def _field_names(entity_context):
    return [field.name for field in entity_context.fields]


def test_root_context_gets_pk_root_scalar_root_fk_and_root_enum_only():
    hierarchy = build_inheritance_hierarchy_context(_vehicle_table(), base_package="com.modelia.generated")

    assert hierarchy.root.class_name == "Vehicle"
    assert hierarchy.root.table_name == "vehicle"
    assert hierarchy.root.extends_class_name is None
    assert hierarchy.root.discriminator_column == "class_type"
    assert hierarchy.root.discriminator_value == "VEHICLE"
    assert _field_names(hierarchy.root) == ["id", "vin", "garage", "fuel"]


def test_subclass_contexts_get_only_matching_owned_fields():
    hierarchy = build_inheritance_hierarchy_context(_vehicle_table(), base_package="com.modelia.generated")

    by_name = {context.class_name: context for context in hierarchy.subclasses}

    assert _field_names(by_name["Car"]) == ["doorCount", "trim"]
    assert _field_names(by_name["PickupTruck"]) == ["payloadCapacity"]
    assert _field_names(by_name["Truck"]) == ["axleCount"]
    for context in hierarchy.subclasses:
        assert "id" not in _field_names(context)
        assert "vin" not in _field_names(context)
        assert "classType" not in _field_names(context)
        assert context.table_name is None
        assert context.extends_class_name == "Vehicle"
        assert context.discriminator_column is None


def test_subclass_class_names_use_pascal_case_class_id_order():
    hierarchy = build_inheritance_hierarchy_context(_vehicle_table(), base_package="com.modelia.generated")

    assert [context.class_name for context in hierarchy.subclasses] == ["Car", "PickupTruck", "Truck"]


def test_imports_are_computed_per_entity_without_same_package_root_import():
    hierarchy = build_inheritance_hierarchy_context(_vehicle_table(), base_package="com.modelia.generated")

    root_imports = {fqn for group in hierarchy.root.import_groups for fqn in group}
    car_imports = {fqn for group in hierarchy.subclasses[0].import_groups for fqn in group}

    assert "jakarta.persistence.Inheritance" in root_imports
    assert "jakarta.persistence.InheritanceType" in root_imports
    assert "jakarta.persistence.DiscriminatorColumn" in root_imports
    assert "jakarta.persistence.DiscriminatorValue" in root_imports
    assert "jakarta.persistence.DiscriminatorColumn" not in car_imports
    assert "com.modelia.generated.domain.Vehicle" not in car_imports


def test_root_repository_context_targets_root_entity():
    hierarchy = build_inheritance_hierarchy_context(_vehicle_table(), base_package="com.modelia.generated")

    assert hierarchy.repository.class_name == "Vehicle"
    assert hierarchy.repository.repository_name == "VehicleRepository"
