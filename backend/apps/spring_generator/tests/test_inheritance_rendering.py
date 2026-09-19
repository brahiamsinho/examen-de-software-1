from apps.relational_mapping.domain.schema import Column, PrimaryKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_table_sources
from apps.spring_generator.tests.factories import a_column


def _vehicle_table(*, discriminator_column: str = "class_type") -> Table:
    return Table(
        name="vehicle",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name=discriminator_column, type=ColumnType.VARCHAR, nullable=False),
            a_column(name="vin", type=ColumnType.VARCHAR, nullable=False, owning_class_id="vehicle"),
            a_column(name="door_count", type=ColumnType.INTEGER, nullable=True, owning_class_id="car"),
            a_column(name="payload_capacity", type=ColumnType.NUMERIC, nullable=True, precision=10, scale=2, owning_class_id="truck"),
        ),
        primary_key=PrimaryKey(column_names=("id",), name="pk_vehicle"),
        source_class_ids=("vehicle", "car", "truck"),
        discriminator_column=discriminator_column,
        discriminator_values={"vehicle": "VEHICLE", "car": "CAR", "truck": "TRUCK"},
    )


def _paths(sources):
    return tuple(generated_file.path for generated_file in sources.files)


def _contents_by_suffix(sources, suffix: str) -> str:
    return next(generated_file.contents for generated_file in sources.files if generated_file.path.endswith(suffix))


def test_supported_hierarchy_emits_only_domain_classes_and_root_repository_in_order():
    sources = generate_table_sources(_vehicle_table())

    assert _paths(sources) == (
        "src/main/java/com/modelia/generated/domain/Vehicle.java",
        "src/main/java/com/modelia/generated/domain/Car.java",
        "src/main/java/com/modelia/generated/domain/Truck.java",
        "src/main/java/com/modelia/generated/persistence/VehicleRepository.java",
    )


def test_generation_is_deterministic_and_byte_identical():
    first = generate_table_sources(_vehicle_table())
    second = generate_table_sources(_vehicle_table())

    assert _paths(first) == _paths(second)
    assert [generated_file.contents for generated_file in first.files] == [
        generated_file.contents for generated_file in second.files
    ]


def test_root_entity_contains_single_table_metadata_and_is_concrete():
    vehicle = _contents_by_suffix(generate_table_sources(_vehicle_table()), "Vehicle.java")

    assert "@Entity" in vehicle
    assert '@Table(name = "vehicle")' in vehicle
    assert "@Inheritance(strategy = InheritanceType.SINGLE_TABLE)" in vehicle
    assert '@DiscriminatorColumn(name = "class_type")' in vehicle
    assert '@DiscriminatorValue("VEHICLE")' in vehicle
    assert "public class Vehicle {" in vehicle
    assert "abstract class Vehicle" not in vehicle


def test_actual_discriminator_column_name_is_metadata_only():
    sources = generate_table_sources(_vehicle_table(discriminator_column="kind"))
    vehicle = _contents_by_suffix(sources, "Vehicle.java")

    assert '@DiscriminatorColumn(name = "kind")' in vehicle
    for generated_file in sources.files:
        assert " kind;" not in generated_file.contents
        assert "getKind()" not in generated_file.contents


def test_subclasses_extend_root_and_partition_fields():
    sources = generate_table_sources(_vehicle_table())
    vehicle = _contents_by_suffix(sources, "Vehicle.java")
    car = _contents_by_suffix(sources, "Car.java")
    truck = _contents_by_suffix(sources, "Truck.java")

    assert "public class Car extends Vehicle {" in car
    assert '@DiscriminatorValue("CAR")' in car
    assert "private Integer doorCount;" in car
    assert "private UUID id;" not in car
    assert "private String vin;" not in car
    assert "payloadCapacity" not in car

    assert "public class Truck extends Vehicle {" in truck
    assert '@DiscriminatorValue("TRUCK")' in truck
    assert "private BigDecimal payloadCapacity;" in truck
    assert "doorCount" not in truck

    assert "private String vin;" in vehicle
    assert "doorCount" not in vehicle
    assert "payloadCapacity" not in vehicle
    assert "classType" not in vehicle


def test_no_dto_service_controller_error_validation_config_or_subclass_repository_paths():
    sources = generate_table_sources(_vehicle_table())

    for path in _paths(sources):
        for forbidden in ("/application/", "/application/dto/", "/api/", "/errors/", "/validation/", "/config/"):
            assert forbidden not in path
    assert not any(path.endswith("CarRepository.java") or path.endswith("TruckRepository.java") for path in _paths(sources))


def test_root_repository_targets_root_entity_only():
    repository = _contents_by_suffix(generate_table_sources(_vehicle_table()), "VehicleRepository.java")

    assert "public interface VehicleRepository extends JpaRepository<Vehicle, UUID>" in repository
    assert "CarRepository" not in repository
    assert "TruckRepository" not in repository
