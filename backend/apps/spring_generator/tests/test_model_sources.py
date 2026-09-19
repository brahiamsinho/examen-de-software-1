from apps.relational_mapping.domain.schema import Column, PrimaryKey, RelationalModel, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import (
    generate_enum_source,
    generate_model_sources,
    generate_project_config_sources,
    generate_shared_error_sources,
    generate_table_sources,
)
from apps.spring_generator.tests.factories import a_column, a_table, an_enum_type


def _paths(sources):
    return tuple(generated_file.path for generated_file in sources.files)


def _expected_files(*, tables=(), enum_types=(), base_package="com.modelia.generated"):
    files = []
    for table in tables:
        files.extend(generate_table_sources(table, base_package=base_package).files)
    for enum_type in enum_types:
        files.append(generate_enum_source(enum_type, base_package=base_package))
    files.extend(generate_shared_error_sources(base_package=base_package).files)
    files.extend(generate_project_config_sources().files)
    return tuple(files)


def _vehicle_table() -> Table:
    return Table(
        name="vehicle",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name="class_type", type=ColumnType.VARCHAR, nullable=False),
            a_column(name="vin", type=ColumnType.VARCHAR, nullable=False, owning_class_id="vehicle"),
            a_column(name="door_count", type=ColumnType.INTEGER, nullable=True, owning_class_id="car"),
            a_column(
                name="payload_capacity",
                type=ColumnType.NUMERIC,
                nullable=True,
                precision=10,
                scale=2,
                owning_class_id="truck",
            ),
        ),
        primary_key=PrimaryKey(column_names=("id",), name="pk_vehicle"),
        source_class_ids=("vehicle", "car", "truck"),
        discriminator_column="class_type",
        discriminator_values={"vehicle": "VEHICLE", "car": "CAR", "truck": "TRUCK"},
    )


def test_public_api_aggregates_tables_then_enums_then_globals_in_order():
    product = a_table(name="product")
    order = a_table(name="order")
    order_status = an_enum_type(name="order_status", labels=("PENDING", "PAID"))
    model = RelationalModel(tables=(product, order), enum_types=(order_status,))

    sources = generate_model_sources(model, base_package="com.example.generated")

    assert sources.files == _expected_files(
        tables=(product, order), enum_types=(order_status,), base_package="com.example.generated"
    )


def test_empty_model_emits_only_shared_errors_then_application_yml():
    sources = generate_model_sources(RelationalModel())

    assert _paths(sources) == _paths(
        generate_shared_error_sources(base_package="com.modelia.generated")
    ) + _paths(generate_project_config_sources())


def test_globals_are_included_exactly_once_for_multiple_tables_and_enums():
    model = RelationalModel(
        tables=(a_table(name="product"), a_table(name="order")),
        enum_types=(
            an_enum_type(name="order_status", labels=("PENDING", "PAID")),
            an_enum_type(name="priority_level", labels=("LOW", "HIGH")),
        ),
    )

    paths = _paths(generate_model_sources(model, base_package="com.example.generated"))

    assert paths.count("src/main/java/com/example/generated/errors/ResourceNotFoundException.java") == 1
    assert paths.count("src/main/java/com/example/generated/errors/GlobalExceptionHandler.java") == 1
    assert paths.count("src/main/resources/application.yml") == 1


def test_custom_package_propagates_to_tables_enums_and_shared_errors_but_not_application_yml():
    table = a_table(name="product")
    enum_type = an_enum_type(name="product_status", labels=("ACTIVE",))
    sources = generate_model_sources(
        RelationalModel(tables=(table,), enum_types=(enum_type,)), base_package="org.example.myproject"
    )

    paths = _paths(sources)
    assert "src/main/java/org/example/myproject/domain/Product.java" in paths
    assert "src/main/java/org/example/myproject/domain/ProductStatus.java" in paths
    assert "src/main/java/org/example/myproject/errors/ResourceNotFoundException.java" in paths
    assert "src/main/resources/application.yml" in paths
    assert all("com/modelia/generated" not in path for path in paths)

    product = sources.file_by_path("src/main/java/org/example/myproject/domain/Product.java")
    product_status = sources.file_by_path("src/main/java/org/example/myproject/domain/ProductStatus.java")
    resource_error = sources.file_by_path(
        "src/main/java/org/example/myproject/errors/ResourceNotFoundException.java"
    )
    application_yml = sources.file_by_path("src/main/resources/application.yml")

    assert "package org.example.myproject.domain;" in product.contents
    assert "package org.example.myproject.domain;" in product_status.contents
    assert "package org.example.myproject.errors;" in resource_error.contents
    assert "org.example.myproject" not in application_yml.contents


def test_lower_level_outputs_are_byte_identical_inside_aggregate():
    table = a_table(name="product")
    enum_type = an_enum_type(name="product_status", labels=("ACTIVE",))
    model = RelationalModel(tables=(table,), enum_types=(enum_type,))

    sources = generate_model_sources(model, base_package="com.example.generated")

    assert sources.files == _expected_files(
        tables=(table,), enum_types=(enum_type,), base_package="com.example.generated"
    )


def test_inheritance_table_boundary_is_preserved_before_next_table_block():
    vehicle = _vehicle_table()
    product = a_table(name="product")
    sources = generate_model_sources(RelationalModel(tables=(vehicle, product)))
    vehicle_files = generate_table_sources(vehicle).files
    product_files = generate_table_sources(product).files

    assert sources.files[: len(vehicle_files)] == vehicle_files
    assert sources.files[len(vehicle_files) : len(vehicle_files) + len(product_files)] == product_files


def test_inheritance_aggregation_adds_no_inheritance_api_expansion_paths():
    sources = generate_model_sources(RelationalModel(tables=(_vehicle_table(),)))
    vehicle_region = sources.files[: len(generate_table_sources(_vehicle_table()).files)]

    for generated_file in vehicle_region:
        for forbidden in ("/application/", "/application/dto/", "/api/", "/validation/", "/config/"):
            assert forbidden not in generated_file.path
    assert not any(
        generated_file.path.endswith("CarRepository.java") or generated_file.path.endswith("TruckRepository.java")
        for generated_file in vehicle_region
    )
