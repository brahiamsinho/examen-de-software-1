"""RED: apps.spring_generator.emit.context does not exist yet.

Covers: `@Column` always emits an explicit `name`; `length` only for
`VARCHAR` with a length; `precision`/`scale` only for `NUMERIC`;
absent values omitted, never defaulted; fixed attribute order `name,
nullable, length, precision, scale, columnDefinition, updatable`
(design.md DD10).
"""
from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_entity_context
from apps.spring_generator.tests.factories import a_table

_PK = Column(name="id", type=ColumnType.UUID, nullable=False)


def _entity_fields(*extra_columns):
    table = a_table(
        columns=(_PK,) + extra_columns, primary_key=PrimaryKey(column_names=("id",), name="pk_product")
    )
    return build_entity_context(table, base_package="com.modelia.generated").fields


def test_column_annotation_always_has_explicit_name():
    fields = _entity_fields(Column(name="title", type=ColumnType.INTEGER, nullable=False))
    field = fields[1]

    column_annotation = next(a for a in field.annotations if a.startswith("@Column"))
    assert 'name = "title"' in column_annotation


def test_varchar_with_length_gets_length_attribute():
    fields = _entity_fields(Column(name="name", type=ColumnType.VARCHAR, nullable=False, length=255))
    field = fields[1]

    column_annotation = next(a for a in field.annotations if a.startswith("@Column"))
    assert "length = 255" in column_annotation


def test_varchar_without_length_has_no_length_attribute():
    fields = _entity_fields(Column(name="name", type=ColumnType.VARCHAR, nullable=False))
    field = fields[1]

    column_annotation = next(a for a in field.annotations if a.startswith("@Column"))
    assert "length" not in column_annotation


def test_numeric_gets_precision_and_scale_when_set():
    fields = _entity_fields(Column(name="price", type=ColumnType.NUMERIC, nullable=False, precision=10, scale=2))
    field = fields[1]

    column_annotation = next(a for a in field.annotations if a.startswith("@Column"))
    assert "precision = 10" in column_annotation
    assert "scale = 2" in column_annotation


def test_numeric_without_precision_scale_omits_them():
    fields = _entity_fields(Column(name="price", type=ColumnType.NUMERIC, nullable=False))
    field = fields[1]

    column_annotation = next(a for a in field.annotations if a.startswith("@Column"))
    assert "precision" not in column_annotation
    assert "scale" not in column_annotation


def test_integer_column_never_gets_length_precision_or_scale():
    fields = _entity_fields(Column(name="quantity", type=ColumnType.INTEGER, nullable=False))
    field = fields[1]

    column_annotation = next(a for a in field.annotations if a.startswith("@Column"))
    assert "length" not in column_annotation
    assert "precision" not in column_annotation
    assert "scale" not in column_annotation


def test_column_attribute_order_is_fixed():
    fields = _entity_fields(
        Column(name="price", type=ColumnType.NUMERIC, nullable=True, precision=10, scale=2)
    )
    field = fields[1]

    column_annotation = next(a for a in field.annotations if a.startswith("@Column"))
    name_index = column_annotation.index("name")
    nullable_index = column_annotation.index("nullable")
    precision_index = column_annotation.index("precision")
    scale_index = column_annotation.index("scale")
    assert name_index < nullable_index < precision_index < scale_index


def test_text_column_gets_column_definition_text():
    fields = _entity_fields(Column(name="notes", type=ColumnType.TEXT, nullable=True))
    field = fields[1]

    column_annotation = next(a for a in field.annotations if a.startswith("@Column"))
    assert 'columnDefinition = "TEXT"' in column_annotation
