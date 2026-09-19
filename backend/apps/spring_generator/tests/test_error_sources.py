"""RED: apps.spring_generator.emit.renderer.generate_shared_error_sources
does not exist yet.

Covers: DD41 (generic `ResourceNotFoundException(String, UUID)`), DD42
(a `Table`-free singleton entry point yielding exactly 2 files, never
emitted by `generate_table_sources`), DD43 (`@RestControllerAdvice`
with two `@ExceptionHandler`s mapped to 404/400 via `ProblemDetail`).
"""
from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_shared_error_sources, generate_table_sources
from apps.spring_generator.tests.factories import a_table


def _product_table():
    return a_table(
        name="product",
        columns=(Column(name="id", type=ColumnType.UUID, nullable=False),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
    )


def test_returns_exactly_two_files_at_the_errors_paths():
    sources = generate_shared_error_sources(base_package="com.modelia.generated")

    assert len(sources.files) == 2
    assert (
        sources.file_by_path("src/main/java/com/modelia/generated/errors/ResourceNotFoundException.java")
        is not None
    )
    assert (
        sources.file_by_path("src/main/java/com/modelia/generated/errors/GlobalExceptionHandler.java")
        is not None
    )


def test_generate_table_sources_emits_nothing_under_errors():
    sources = generate_table_sources(_product_table())

    for generated_file in sources.files:
        assert "/errors/" not in generated_file.path


def test_resource_not_found_exception_extends_runtime_exception_with_string_uuid_ctor():
    sources = generate_shared_error_sources(base_package="com.modelia.generated")
    exception_source = sources.file_by_path(
        "src/main/java/com/modelia/generated/errors/ResourceNotFoundException.java"
    ).contents

    assert "class ResourceNotFoundException extends RuntimeException" in exception_source
    assert "public ResourceNotFoundException(String resourceName, UUID id)" in exception_source


def test_global_exception_handler_is_rest_controller_advice_not_bare_controller_advice():
    sources = generate_shared_error_sources(base_package="com.modelia.generated")
    handler_source = sources.file_by_path(
        "src/main/java/com/modelia/generated/errors/GlobalExceptionHandler.java"
    ).contents

    assert "@RestControllerAdvice" in handler_source
    assert "@ControllerAdvice" not in handler_source


def test_global_exception_handler_maps_both_exceptions_via_problem_detail():
    sources = generate_shared_error_sources(base_package="com.modelia.generated")
    handler_source = sources.file_by_path(
        "src/main/java/com/modelia/generated/errors/GlobalExceptionHandler.java"
    ).contents

    assert "@ExceptionHandler(ResourceNotFoundException.class)" in handler_source
    assert "@ExceptionHandler(MethodArgumentNotValidException.class)" in handler_source
    assert "ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND" in handler_source
    assert "ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST" in handler_source
    assert "ProblemDetail" in handler_source


def test_repeated_invocation_is_byte_identical():
    first = generate_shared_error_sources(base_package="com.modelia.generated")
    second = generate_shared_error_sources(base_package="com.modelia.generated")

    assert first == second
    for first_file, second_file in zip(first.files, second.files):
        assert first_file.contents == second_file.contents


def test_custom_base_package_is_honored():
    sources = generate_shared_error_sources(base_package="org.example.myproject")

    assert (
        sources.file_by_path("src/main/java/org/example/myproject/errors/ResourceNotFoundException.java")
        is not None
    )
    exception_source = sources.file_by_path(
        "src/main/java/org/example/myproject/errors/ResourceNotFoundException.java"
    ).contents
    assert "package org.example.myproject.errors;" in exception_source
