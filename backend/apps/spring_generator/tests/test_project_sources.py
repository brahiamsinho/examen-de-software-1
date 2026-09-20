"""Contract of `generate_project_sources` (DD69-DD71, DD74): the model
aggregate followed by the three scaffold files, with one duplicate-path check
over the combined tuple.
"""
import pytest

from apps.relational_mapping.domain.schema import Column, PrimaryKey, RelationalModel, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.domain.sources import GeneratedFile, GeneratedSources
from apps.spring_generator.emit import renderer
from apps.spring_generator.emit.errors import GeneratedSourcePathCollisionError, UngeneratableSourceError
from apps.spring_generator.tests.factories import a_column, a_table, an_enum_type

_BASE = "com.example.generated"
_LAYER_DIRS = ("domain/", "persistence/", "application/", "api/", "errors/")


def _model() -> RelationalModel:
    return RelationalModel(
        tables=(a_table(name="product"), a_table(name="order")),
        enum_types=(an_enum_type(name="order_status", labels=("PENDING", "PAID")),),
    )


def _discriminator_table() -> Table:
    return Table(
        name="vehicle",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name="class_type", type=ColumnType.VARCHAR, nullable=False),
            a_column(name="vin", type=ColumnType.VARCHAR, nullable=False, owning_class_id="vehicle"),
            a_column(name="door_count", type=ColumnType.INTEGER, nullable=True, owning_class_id="car"),
        ),
        primary_key=PrimaryKey(column_names=("id",), name="pk_vehicle"),
        source_class_ids=("vehicle", "car"),
        discriminator_column="class_type",
        discriminator_values={"vehicle": "Vehicle", "car": "Car"},
    )


def _uuid_hierarchy_table() -> Table:
    # Digit-leading uuid4-hex element ids, as the editor produces them. Class names must come from
    # the discriminator values (the UML class names), never from these ids.
    vehicle_id = "1b4e28ba2fa14b2f8d5e6c1a9f3d7e01"
    car_id = "7c9e6679742540de944be27a4a4b2c11"
    truck_id = "0f8fad5bd9cb469fa16570867728950e"
    return Table(
        name="vehicle",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name="class_type", type=ColumnType.VARCHAR, nullable=False),
            a_column(name="vin", type=ColumnType.VARCHAR, nullable=False, owning_class_id=vehicle_id),
            a_column(name="door_count", type=ColumnType.INTEGER, nullable=True, owning_class_id=car_id),
            a_column(name="axle_count", type=ColumnType.INTEGER, nullable=True, owning_class_id=truck_id),
        ),
        primary_key=PrimaryKey(column_names=("id",), name="pk_vehicle"),
        source_class_ids=(vehicle_id, car_id, truck_id),
        discriminator_column="class_type",
        discriminator_values={vehicle_id: "Vehicle", car_id: "Car", truck_id: "Truck"},
    )


def _paths(sources: GeneratedSources) -> list[str]:
    return [generated_file.path for generated_file in sources.files]


# ---- composition ---------------------------------------------------------------------


def test_files_are_the_model_aggregate_followed_by_the_scaffold():
    model = _model()
    model_files = renderer.generate_model_sources(model, base_package=_BASE).files
    scaffold_files = renderer.generate_project_scaffold_sources(base_package=_BASE).files

    sources = renderer.generate_project_sources(model, base_package=_BASE)

    assert len(scaffold_files) == 3
    assert sources.files[: len(model_files)] == model_files
    assert sources.files[len(model_files) :] == scaffold_files
    assert sources.files == model_files + scaffold_files


def test_project_aggregate_has_no_extra_files_beyond_model_and_scaffold():
    model = _model()
    model_count = len(renderer.generate_model_sources(model, base_package=_BASE).files)

    sources = renderer.generate_project_sources(model, base_package=_BASE)

    assert len(sources.files) == model_count + 3


def test_default_base_package_matches_the_other_entry_points():
    model = _model()

    assert renderer.generate_project_sources(model) == renderer.generate_project_sources(
        model, base_package="com.modelia.generated"
    )
    assert renderer.generate_project_sources(model).files[-1].path == (
        "src/main/java/com/modelia/generated/Application.java"
    )


def test_empty_model_yields_errors_then_application_yml_then_the_scaffold():
    sources = renderer.generate_project_sources(RelationalModel(), base_package=_BASE)

    assert _paths(sources) == [
        "src/main/java/com/example/generated/errors/ResourceNotFoundException.java",
        "src/main/java/com/example/generated/errors/GlobalExceptionHandler.java",
        "src/main/resources/application.yml",
        "build.gradle",
        "settings.gradle",
        "src/main/java/com/example/generated/Application.java",
    ]


def test_uuid_id_hierarchy_emits_subclass_files_named_after_the_uml_class_names():
    model = RelationalModel(tables=(_uuid_hierarchy_table(),))

    sources = renderer.generate_project_sources(model, base_package=_BASE)

    paths = _paths(sources)
    root = "src/main/java/com/example/generated/domain/"
    assert root + "Vehicle.java" in paths
    assert root + "Car.java" in paths
    assert root + "Truck.java" in paths
    assert 'class Car extends Vehicle' in sources.file_by_path(root + "Car.java").contents
    assert 'class Truck extends Vehicle' in sources.file_by_path(root + "Truck.java").contents


def test_scaffold_tail_is_identical_to_the_standalone_scaffold_output():
    sources = renderer.generate_project_sources(_model(), base_package="org.example.app")

    assert sources.files[-3:] == renderer.generate_project_scaffold_sources(base_package="org.example.app").files


def test_model_aggregate_output_is_unchanged_and_contains_no_scaffold_path():
    paths = _paths(renderer.generate_model_sources(_model(), base_package=_BASE))

    assert "build.gradle" not in paths
    assert "settings.gradle" not in paths
    assert "src/main/java/com/example/generated/Application.java" not in paths


@pytest.mark.parametrize("invalid", ["Com.Bad", "com-example", "", "1bad"])
def test_invalid_base_package_is_rejected_without_output(invalid):
    with pytest.raises(ValueError):
        renderer.generate_project_sources(_model(), base_package=invalid)


def test_repeated_project_generation_is_byte_identical():
    first = renderer.generate_project_sources(_model(), base_package=_BASE)
    second = renderer.generate_project_sources(_model(), base_package=_BASE)

    assert first == second
    assert [f.contents for f in first.files] == [f.contents for f in second.files]


# ---- file placement -----------------------------------------------------------------------


def test_application_java_is_the_single_java_file_outside_the_six_layers():
    sources = renderer.generate_project_sources(_model(), base_package=_BASE)
    root = "src/main/java/com/example/generated/"

    java_outside_layers = [
        path
        for path in _paths(sources)
        if path.endswith(".java") and not path.removeprefix(root).startswith(_LAYER_DIRS)
    ]

    assert java_outside_layers == ["src/main/java/com/example/generated/Application.java"]
    non_java = [path for path in _paths(sources) if not path.endswith(".java")]
    assert non_java == ["src/main/resources/application.yml", "build.gradle", "settings.gradle"]


def test_no_validation_or_config_directory_is_produced():
    sources = renderer.generate_project_sources(_model(), base_package=_BASE)

    assert len(sources.files) == 19
    for path in _paths(sources):
        assert "/validation/" not in path
        assert "/config/" not in path


def test_existing_entry_points_never_emit_a_scaffold_path():
    scaffold_paths = {
        "build.gradle",
        "settings.gradle",
        "src/main/java/com/modelia/generated/Application.java",
    }
    plain = renderer.generate_table_sources(a_table(name="product"))
    hierarchy = renderer.generate_table_sources(_discriminator_table())
    errors = renderer.generate_shared_error_sources()
    config = renderer.generate_project_config_sources()

    for sources in (plain, hierarchy, errors, config):
        assert len(sources.files) >= 1
        assert scaffold_paths.isdisjoint(_paths(sources))


# ---- DD71 collision seam -----------------------------------------------------------------------


def test_scaffold_path_colliding_with_a_model_path_is_rejected_atomically(monkeypatch):
    colliding_path = "src/main/java/com/example/generated/domain/Product.java"
    monkeypatch.setattr(
        renderer,
        "generate_project_scaffold_sources",
        lambda *, base_package: GeneratedSources(files=(GeneratedFile(path=colliding_path, contents="x"),)),
    )

    with pytest.raises(GeneratedSourcePathCollisionError) as excinfo:
        renderer.generate_project_sources(_model(), base_package=_BASE)

    assert isinstance(excinfo.value, UngeneratableSourceError)
    assert excinfo.value.path == colliding_path
    assert excinfo.value.occurrences == 2


def test_model_level_duplicate_propagates_and_the_scaffold_is_never_generated(monkeypatch):
    calls: list[str] = []

    def _spy_scaffold(*, base_package):
        calls.append(base_package)
        return GeneratedSources()

    monkeypatch.setattr(renderer, "generate_project_scaffold_sources", _spy_scaffold)
    colliding_model = RelationalModel(
        tables=(a_table(name="status"),),
        enum_types=(an_enum_type(name="status", labels=("ACTIVE",)),),
    )

    with pytest.raises(GeneratedSourcePathCollisionError) as excinfo:
        renderer.generate_project_sources(colliding_model, base_package=_BASE)

    assert excinfo.value.path == "src/main/java/com/example/generated/domain/Status.java"
    assert excinfo.value.occurrences == 2
    assert calls == []


def test_project_aggregate_calls_its_collaborators_by_module_global_name(monkeypatch):
    marker = GeneratedFile(path="build.gradle", contents="patched")
    monkeypatch.setattr(
        renderer,
        "generate_project_scaffold_sources",
        lambda *, base_package: GeneratedSources(files=(marker,)),
    )

    sources = renderer.generate_project_sources(RelationalModel(), base_package=_BASE)

    assert sources.files[-1] == marker
    assert len(sources.files) == 4


def test_duplicate_path_helper_rejects_a_hand_built_tuple_with_build_gradle_twice():
    files = (
        GeneratedFile(path="build.gradle", contents="a"),
        GeneratedFile(path="settings.gradle", contents="b"),
        GeneratedFile(path="build.gradle", contents="c"),
    )

    with pytest.raises(GeneratedSourcePathCollisionError) as excinfo:
        renderer._reject_duplicate_generated_paths(files)

    assert excinfo.value.path == "build.gradle"
    assert excinfo.value.occurrences == 2
