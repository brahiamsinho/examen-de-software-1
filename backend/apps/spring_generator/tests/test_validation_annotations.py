"""RED: apps.spring_generator.emit.context does not exist yet.

Covers: `nullable=False` -> `@NotNull`; `nullable=True` -> none;
`@Size(max=)` from `length`; `@NotBlank` never appears; validation
imports present only when used (design.md DD9).
"""
from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_entity_context
from apps.spring_generator.tests.factories import a_table

_PK = Column(name="id", type=ColumnType.UUID, nullable=False)


def _build(*extra_columns):
    table = a_table(
        columns=(_PK,) + extra_columns, primary_key=PrimaryKey(column_names=("id",), name="pk_product")
    )
    return build_entity_context(table, base_package="com.modelia.generated")


def test_not_nullable_column_gets_not_null():
    context = _build(Column(name="title", type=ColumnType.VARCHAR, nullable=False))
    field = context.fields[1]

    assert "@NotNull" in field.annotations


def test_nullable_column_has_no_not_null():
    context = _build(Column(name="title", type=ColumnType.VARCHAR, nullable=True))
    field = context.fields[1]

    assert "@NotNull" not in field.annotations


def test_varchar_with_length_gets_size_annotation():
    context = _build(Column(name="title", type=ColumnType.VARCHAR, nullable=False, length=120))
    field = context.fields[1]

    assert "@Size(max = 120)" in field.annotations


def test_not_blank_never_appears():
    context = _build(
        Column(name="title", type=ColumnType.VARCHAR, nullable=False, length=120),
        Column(name="notes", type=ColumnType.TEXT, nullable=True),
    )

    for field in context.fields:
        assert not any("NotBlank" in annotation for annotation in field.annotations)


def test_validation_imports_present_only_when_used():
    context_with_validation = _build(Column(name="title", type=ColumnType.VARCHAR, nullable=False, length=120))
    flat_imports = {fqn for group in context_with_validation.import_groups for fqn in group}
    assert "jakarta.validation.constraints.NotNull" in flat_imports
    assert "jakarta.validation.constraints.Size" in flat_imports


def test_no_validation_imports_when_all_columns_nullable_and_unbounded():
    context_without_validation = _build(Column(name="notes", type=ColumnType.TEXT, nullable=True))
    flat_imports = {fqn for group in context_without_validation.import_groups for fqn in group}
    assert "jakarta.validation.constraints.NotNull" not in flat_imports
    assert "jakarta.validation.constraints.Size" not in flat_imports
