"""RED: `generate_table_sources` still emits only 2 files; this module
now requires all 6 (design.md DD50a layer order).

Covers: all six files at their DD37/DD50a paths, in fixed layer order
`domain, persistence, application/dto (request), application/dto
(response), application, api`; each `package` declaration matches its
path; custom `base_package` honored across all six; invalid
`base_package` rejected; no host/port/URL substring in any output
(design.md DD20). Also covers spec "Package and File Path Layout":
no file under `validation/`, `config/`, or `errors/` (DD42 reserves
`errors/` for `generate_shared_error_sources`).
"""
import pytest

from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_table_sources
from apps.spring_generator.tests.factories import a_table, searchable


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
    assert (
        sources.file_by_path("src/main/java/com/modelia/generated/application/dto/ProductRequestDto.java")
        is not None
    )
    assert (
        sources.file_by_path("src/main/java/com/modelia/generated/application/dto/ProductResponseDto.java")
        is not None
    )
    assert (
        sources.file_by_path("src/main/java/com/modelia/generated/application/ProductService.java") is not None
    )
    assert sources.file_by_path("src/main/java/com/modelia/generated/api/ProductController.java") is not None


def test_generate_table_sources_yields_exactly_six_files_in_fixed_layer_order():
    sources = generate_table_sources(_product_table())

    expected_order = (
        "src/main/java/com/modelia/generated/domain/Product.java",
        "src/main/java/com/modelia/generated/persistence/ProductRepository.java",
        "src/main/java/com/modelia/generated/application/dto/ProductRequestDto.java",
        "src/main/java/com/modelia/generated/application/dto/ProductResponseDto.java",
        "src/main/java/com/modelia/generated/application/ProductService.java",
        "src/main/java/com/modelia/generated/api/ProductController.java",
    )
    assert tuple(generated_file.path for generated_file in sources.files) == expected_order
    assert len(sources.files) == 6


def test_no_file_under_validation_config_or_errors():
    sources = generate_table_sources(_product_table())

    for generated_file in sources.files:
        for forbidden in ("/validation/", "/config/", "/errors/"):
            assert forbidden not in generated_file.path


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


def test_dto_service_and_controller_package_declarations_match_path():
    sources = generate_table_sources(_product_table())

    request_dto_source = sources.file_by_path(
        "src/main/java/com/modelia/generated/application/dto/ProductRequestDto.java"
    ).contents
    response_dto_source = sources.file_by_path(
        "src/main/java/com/modelia/generated/application/dto/ProductResponseDto.java"
    ).contents
    service_source = sources.file_by_path(
        "src/main/java/com/modelia/generated/application/ProductService.java"
    ).contents
    controller_source = sources.file_by_path(
        "src/main/java/com/modelia/generated/api/ProductController.java"
    ).contents

    assert "package com.modelia.generated.application.dto;" in request_dto_source
    assert "package com.modelia.generated.application.dto;" in response_dto_source
    assert "package com.modelia.generated.application;" in service_source
    assert "package com.modelia.generated.api;" in controller_source


def test_custom_base_package_is_honored():
    sources = generate_table_sources(_product_table(), base_package="org.example.myproject")

    assert sources.file_by_path("src/main/java/org/example/myproject/domain/Product.java") is not None
    entity_source = sources.file_by_path("src/main/java/org/example/myproject/domain/Product.java").contents
    assert "package org.example.myproject.domain;" in entity_source

    assert (
        sources.file_by_path("src/main/java/org/example/myproject/application/dto/ProductRequestDto.java")
        is not None
    )
    assert (
        sources.file_by_path("src/main/java/org/example/myproject/application/dto/ProductResponseDto.java")
        is not None
    )
    assert (
        sources.file_by_path("src/main/java/org/example/myproject/application/ProductService.java") is not None
    )
    assert sources.file_by_path("src/main/java/org/example/myproject/api/ProductController.java") is not None


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


def test_searchable_table_yields_exactly_one_extra_specification_file():
    table = a_table(name="customer", columns=(Column(name="name", type=ColumnType.VARCHAR, profile=searchable()),))

    sources = generate_table_sources(table)

    expected_order = (
        "src/main/java/com/modelia/generated/domain/Customer.java",
        "src/main/java/com/modelia/generated/persistence/CustomerRepository.java",
        "src/main/java/com/modelia/generated/application/dto/CustomerRequestDto.java",
        "src/main/java/com/modelia/generated/application/dto/CustomerResponseDto.java",
        "src/main/java/com/modelia/generated/application/CustomerService.java",
        "src/main/java/com/modelia/generated/api/CustomerController.java",
        "src/main/java/com/modelia/generated/application/CustomerSpecifications.java",
    )
    assert tuple(generated_file.path for generated_file in sources.files) == expected_order
    assert len(sources.files) == 7
