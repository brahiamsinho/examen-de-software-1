"""RED: apps.spring_generator.emit.context does not exist yet.

Covers: the PK field gets `@Id` + `@GeneratedValue(strategy =
GenerationType.UUID)` + `@Column(..., updatable = false)`, and the PK
field never gets `@NotNull` (design.md DD8) — Bean Validation would
otherwise fire before the provider generates the id on `persist()`.
"""
from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_entity_context
from apps.spring_generator.tests.factories import a_table


def test_primary_key_field_gets_id_and_generated_value():
    table = a_table(
        columns=(Column(name="id", type=ColumnType.UUID, nullable=False),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    pk_field = context.fields[0]

    assert pk_field.annotations[0] == "@Id"
    assert pk_field.annotations[1] == "@GeneratedValue(strategy = GenerationType.UUID)"


def test_primary_key_column_annotation_has_updatable_false():
    table = a_table(
        columns=(Column(name="id", type=ColumnType.UUID, nullable=False),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    pk_field = context.fields[0]

    column_annotation = next(a for a in pk_field.annotations if a.startswith("@Column"))
    assert 'name = "id"' in column_annotation
    assert "nullable = false" in column_annotation
    assert "updatable = false" in column_annotation


def test_primary_key_field_never_gets_not_null():
    table = a_table(
        columns=(Column(name="id", type=ColumnType.UUID, nullable=False),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    pk_field = context.fields[0]

    assert "@NotNull" not in pk_field.annotations
