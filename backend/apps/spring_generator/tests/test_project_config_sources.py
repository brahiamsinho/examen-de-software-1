import re

import pytest

from apps.spring_generator.domain.sources import GeneratedSources
from apps.spring_generator.emit import renderer
from apps.spring_generator.tests.factories import a_column, a_primary_key, a_table
from apps.relational_mapping.domain.types import ColumnType

_APPLICATION_YML_PATH = "src/main/resources/application.yml"
_REQUIRED_LINES = (
    "    name: ${SPRING_APPLICATION_NAME}",
    "    url: ${SPRING_DATASOURCE_URL}",
    "    username: ${SPRING_DATASOURCE_USERNAME}",
    "    password: ${SPRING_DATASOURCE_PASSWORD}",
    "      ddl-auto: ${JPA_DDL_AUTO}",
    "  port: ${SERVER_PORT}",
)
_LAYER_PREFIXES = (
    "domain/",
    "persistence/",
    "application/",
    "application/dto/",
    "api/",
    "errors/",
    "validation/",
    "config/",
)


def _project_config_sources():
    return renderer.generate_project_config_sources()


def _application_yml():
    sources = _project_config_sources()
    assert len(sources.files) == 1
    return sources.files[0]


def _supported_non_discriminator_table():
    return a_table(
        columns=(
            a_column(name="id", type=ColumnType.UUID, nullable=False),
            a_column(name="name", type=ColumnType.VARCHAR, nullable=False, length=120),
        ),
        primary_key=a_primary_key(column_names=("id",), name="pk_product"),
    )


def test_generate_project_config_sources_public_entry_point_exists():
    assert hasattr(renderer, "generate_project_config_sources")


def test_returns_exactly_one_application_yml_file():
    sources = _project_config_sources()

    assert isinstance(sources, GeneratedSources)
    assert [generated_file.path for generated_file in sources.files] == [_APPLICATION_YML_PATH]


def test_application_yml_contains_no_java_package_declaration():
    generated_file = _application_yml()

    assert "package " not in generated_file.contents
    assert "package;" not in generated_file.contents


def test_application_yml_contains_required_no_default_placeholders():
    generated_file = _application_yml()

    for line in _REQUIRED_LINES:
        assert line in generated_file.contents


def test_application_yml_contains_no_placeholder_defaults():
    generated_file = _application_yml()

    assert re.search(r"\$\{[A-Z0-9_]+:[^}]+\}", generated_file.contents) is None


def test_application_yml_contains_no_hardcoded_deployable_values():
    generated_file = _application_yml()
    lowered = generated_file.contents.lower()

    forbidden_literals = (
        "localhost",
        "db",
        "postgres",
        "5432",
        "8080",
        "0.0.0.0",
        "http://",
        "https://",
        "jdbc:",
        "admin",
        "root",
        "secret",
    )
    for literal in forbidden_literals:
        assert literal not in lowered


def test_application_yml_omits_dialect_and_platform():
    generated_file = _application_yml()
    lowered = generated_file.contents.lower()

    assert "dialect" not in lowered
    assert "database-platform" not in lowered
    assert "hibernate.dialect" not in lowered


def test_application_yml_omits_excluded_scopes():
    generated_file = _application_yml()
    lowered = generated_file.contents.lower()

    for excluded in ("openapi", "springdoc", "postman", "manifest", "frontend", "mobile", "logging", "docker"):
        assert excluded not in lowered
    assert "@configuration" not in lowered


def test_project_config_generator_emits_no_table_or_shared_error_artifacts():
    sources = _project_config_sources()

    for generated_file in sources.files:
        assert generated_file.path == _APPLICATION_YML_PATH
        assert not any(generated_file.path.startswith(prefix) for prefix in _LAYER_PREFIXES)
        assert not generated_file.path.endswith(".java")


def test_table_generation_does_not_emit_resources():
    sources = renderer.generate_table_sources(_supported_non_discriminator_table())

    assert _APPLICATION_YML_PATH not in [generated_file.path for generated_file in sources.files]
    assert all(not generated_file.path.startswith("src/main/resources/") for generated_file in sources.files)


def test_shared_error_generation_does_not_emit_resources():
    sources = renderer.generate_shared_error_sources(base_package="com.modelia.generated")

    assert len(sources.files) == 2
    assert all("/errors/" in generated_file.path for generated_file in sources.files)
    assert all(generated_file.path.endswith(".java") for generated_file in sources.files)
    assert all(not generated_file.path.startswith("src/main/resources/") for generated_file in sources.files)
