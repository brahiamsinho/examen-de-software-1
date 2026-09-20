"""DD81: the sample model feeds the real pipeline and the compile gate.

Only the runner app's own builder is used (no cross-app test imports). The
expected file count is the slice-0 spike oracle (41 files compiled by Gradle).
"""
import re

from apps.generation_runner.samples.sample_model import build_sample_model, build_sample_relational_model
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_project_sources
from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.types import EnumerationRef, PrimitiveType

BASE_PACKAGE = "com.modelia.generated"
UUID_HEX = re.compile(r"^[0-9a-f]{32}$")
EXPECTED_FILE_COUNT = 41


def _generate():
    return generate_project_sources(build_sample_relational_model(), base_package=BASE_PACKAGE)


def test_sample_model_generates_the_expected_project_files():
    sources = _generate()
    paths = [generated_file.path for generated_file in sources.files]

    assert "build.gradle" in paths
    assert "settings.gradle" in paths
    assert len(paths) == len(set(paths))
    assert len(sources.files) == EXPECTED_FILE_COUNT


def test_generation_from_the_sample_model_is_deterministic():
    assert _generate() == _generate()
    assert build_sample_model() == build_sample_model()


def test_sample_model_covers_scalar_types_and_an_enum():
    model = build_sample_model()
    used_types = {attribute.type for uml_class in model.classes for attribute in uml_class.attributes}

    assert {
        PrimitiveType.STRING,
        PrimitiveType.TEXT,
        PrimitiveType.INTEGER,
        PrimitiveType.DECIMAL,
        PrimitiveType.BOOLEAN,
        PrimitiveType.DATETIME,
    } <= used_types
    assert any(isinstance(attribute_type, EnumerationRef) for attribute_type in used_types)
    assert len(model.enumerations) == 1
    assert model.enumerations[0].literals


def test_sample_model_covers_many_to_one_generalization_and_many_to_many():
    model = build_sample_model()
    associations = [r for r in model.relationships if r.kind is RelationshipKind.ASSOCIATION]
    generalizations = [r for r in model.relationships if r.kind is RelationshipKind.GENERALIZATION]

    def is_many(end):
        return end.multiplicity.upper is None or end.multiplicity.upper > 1

    many_to_one = [r for r in associations if is_many(r.source) != is_many(r.target)]
    many_to_many = [r for r in associations if is_many(r.source) and is_many(r.target)]

    assert len(many_to_one) >= 1
    assert len(many_to_many) == 1
    assert len(generalizations) == 2


def test_relational_model_has_a_single_table_hierarchy_an_enum_and_a_join_table():
    relational = build_sample_relational_model()

    hierarchy_tables = [table for table in relational.tables if table.discriminator_column is not None]
    assert len(hierarchy_tables) == 1
    assert len(hierarchy_tables[0].source_class_ids) == 3

    assert len(relational.enum_types) == 1
    assert any(column.type is ColumnType.ENUM for table in relational.tables for column in table.columns)

    join_tables = [table for table in relational.tables if len(table.foreign_keys) == 2]
    assert len(join_tables) == 1


def test_class_ids_are_frozen_uuid_hex_literals():
    # DD90: the ids look like the ones the editor produces (`new_id()`), but are frozen literals so the
    # sample stays deterministic across processes.
    model = build_sample_model()

    assert model.classes
    assert all(UUID_HEX.match(uml_class.id) for uml_class in model.classes)


def test_every_hierarchy_class_id_starts_with_a_digit():
    # A digit-leading id can never be a legal Java identifier, so the compile gate exercises the exact
    # shape that used to break subclass naming (DD87, DD91).
    model = build_sample_model()
    ids_by_name = {uml_class.name: uml_class.id for uml_class in model.classes}

    for hierarchy_class_name in ("Vehicle", "Car", "Truck"):
        assert ids_by_name[hierarchy_class_name][0].isdigit(), hierarchy_class_name


def test_generated_hierarchy_files_are_named_after_the_uml_classes_not_their_ids():
    paths = [generated_file.path for generated_file in _generate().files]
    domain = "src/main/java/com/modelia/generated/domain/"

    for class_name in ("Vehicle", "Car", "Truck"):
        assert domain + class_name + ".java" in paths
