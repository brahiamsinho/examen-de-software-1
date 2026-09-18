"""RED: apps.spring_generator.emit.renderer does not exist yet.

Covers: both files at `src/main/java/<pkg path>/{domain,persistence}/...`;
`package` declaration matches the path; custom `base_package` honored;
invalid `base_package` rejected; no host/port/URL substring in any
output (design.md DD20). Also covers spec "Package and File Path
Layout": only `domain/` and `persistence/` files are produced.
"""
import pytest

from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_table_sources
from apps.spring_generator.tests.factories import a_table


def _product_table():
    return a_table(
        name="product",
        columns=(Column(name="id", type=ColumnType.UUID, nullable=False),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
    )


def test_default_base_package_paths():
    sources = generate_table_sources(_product_table())

    assert sources.file_by_path("src/main/java/com/modelia/generated/domain/Product.java") is not None
    assert (
        sources.file_by_path("src/main/java/com/modelia/generated/persistence/ProductRepository.java")
        is not None
    )


def test_only_domain_and_persistence_files_are_produced():
    sources = generate_table_sources(_product_table())

    for generated_file in sources.files:
        assert "/domain/" in generated_file.path or "/persistence/" in generated_file.path
        for forbidden in ("/application/", "/api/", "/validation/", "/errors/", "/config/"):
            assert forbidden not in generated_file.path
    assert len(sources.files) == 2


def test_entity_package_declaration_matches_path():
    sources = generate_table_sources(_product_table())
    entity_source = sources.file_by_path("src/main/java/com/modelia/generated/domain/Product.java").contents

    assert "package com.modelia.generated.domain;" in entity_source


def test_repository_package_declaration_matches_path():
    sources = generate_table_sources(_product_table())
    repository_source = sources.file_by_path(
        "src/main/java/com/modelia/generated/persistence/ProductRepository.java"
    ).contents

    assert "package com.modelia.generated.persistence;" in repository_source


def test_custom_base_package_is_honored():
    sources = generate_table_sources(_product_table(), base_package="org.example.myproject")

    assert sources.file_by_path("src/main/java/org/example/myproject/domain/Product.java") is not None
    entity_source = sources.file_by_path("src/main/java/org/example/myproject/domain/Product.java").contents
    assert "package org.example.myproject.domain;" in entity_source


@pytest.mark.parametrize(
    "invalid_package", ["Com.Modelia.Generated", "com..modelia", "1com.modelia", "com/modelia", ""]
)
def test_invalid_base_package_is_rejected(invalid_package):
    with pytest.raises(ValueError):
        generate_table_sources(_product_table(), base_package=invalid_package)


def test_no_host_port_or_url_substring_in_output():
    sources = generate_table_sources(_product_table())

    for generated_file in sources.files:
        lowered = generated_file.contents.lower()
        for forbidden in ("localhost", "http://", "https://", "5432", "8080", "0.0.0.0"):
            assert forbidden not in lowered
