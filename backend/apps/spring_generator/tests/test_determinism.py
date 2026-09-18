"""Property tests for the spec's determinism criterion (design.md DD12,
DD36): (a) repeated calls are byte-identical, (b) field order ==
`table.columns` declaration order (one field per column, DD23), (c)
imports deduped/grouped/sorted, (d) braces and parens balanced in
every emitted file. Strategies widened to FK-bearing and enum-bearing
tables (DD36 — no new ordering rule needed, this file is the proof).
"""
from hypothesis import given, strategies as st

from apps.relational_mapping.domain.schema import Column, EnumType, ForeignKey, PrimaryKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_entity_context
from apps.spring_generator.emit.naming import camel_case, relationship_base_name
from apps.spring_generator.emit.renderer import generate_enum_source, generate_table_sources

_TABLE_NAMES = ["product", "order_item", "customer", "invoice"]
_COLUMN_NAMES = ["name", "description", "quantity", "amount", "notes", "active"]
_NON_ENUM_TYPES = [column_type for column_type in ColumnType if column_type is not ColumnType.ENUM]
_FK_COLUMN_NAMES = ["category_id", "owner_id", "parent_id"]
_ENUM_COLUMN_NAMES = ["status", "priority"]
_ENUM_TYPE_NAMES = ["order_status", "priority_level"]
_ENUM_LABELS = ["PENDING", "PAID", "SHIPPED", "CANCELLED", "IN_PROGRESS"]


@st.composite
def _extra_columns(draw):
    names = draw(st.lists(st.sampled_from(_COLUMN_NAMES), unique=True, max_size=4))
    columns = []
    for name in names:
        column_type = draw(st.sampled_from(_NON_ENUM_TYPES))
        nullable = draw(st.booleans())
        length = None
        precision = None
        scale = None
        if column_type is ColumnType.VARCHAR and draw(st.booleans()):
            length = draw(st.integers(min_value=1, max_value=500))
        if column_type is ColumnType.NUMERIC and draw(st.booleans()):
            precision = draw(st.integers(min_value=1, max_value=20))
            scale = draw(st.integers(min_value=0, max_value=precision))
        columns.append(
            Column(name=name, type=column_type, nullable=nullable, length=length, precision=precision, scale=scale)
        )
    return tuple(columns)


@st.composite
def _relationship_columns(draw):
    fk_column_names = draw(st.lists(st.sampled_from(_FK_COLUMN_NAMES), unique=True, max_size=2))
    columns = []
    foreign_keys = []
    for fk_column_name in fk_column_names:
        referenced_table = relationship_base_name(fk_column_name)
        nullable = draw(st.booleans())
        columns.append(Column(name=fk_column_name, type=ColumnType.UUID, nullable=nullable))
        foreign_keys.append(
            ForeignKey(
                name="fk_{}".format(fk_column_name),
                column_names=(fk_column_name,),
                referenced_table=referenced_table,
                referenced_column_names=("id",),
            )
        )
    return tuple(columns), tuple(foreign_keys)


@st.composite
def _enum_columns(draw):
    names = draw(st.lists(st.sampled_from(_ENUM_COLUMN_NAMES), unique=True, max_size=2))
    columns = []
    for name in names:
        enum_type_name = draw(st.sampled_from(_ENUM_TYPE_NAMES))
        nullable = draw(st.booleans())
        columns.append(Column(name=name, type=ColumnType.ENUM, nullable=nullable, enum_type_name=enum_type_name))
    return tuple(columns)


@st.composite
def _tables(draw):
    table_name = draw(st.sampled_from(_TABLE_NAMES))
    extra_columns = draw(_extra_columns())
    relationship_columns, foreign_keys = draw(_relationship_columns())
    enum_columns = draw(_enum_columns())
    columns = (
        (Column(name="id", type=ColumnType.UUID, nullable=False),)
        + extra_columns
        + relationship_columns
        + enum_columns
    )
    return Table(
        name=table_name,
        columns=columns,
        primary_key=PrimaryKey(column_names=("id",), name=f"pk_{table_name}"),
        foreign_keys=foreign_keys,
    )


@st.composite
def _enum_types(draw):
    name = draw(st.sampled_from(_ENUM_TYPE_NAMES))
    labels = draw(st.lists(st.sampled_from(_ENUM_LABELS), unique=True, min_size=1, max_size=4))
    return EnumType(name=name, labels=tuple(labels))


def _expected_field_name(column: Column, table: Table) -> str:
    if column.name == table.primary_key.column_names[0]:
        return camel_case(column.name)
    foreign_key = next((fk for fk in table.foreign_keys if column.name in fk.column_names), None)
    if foreign_key is not None:
        return camel_case(relationship_base_name(column.name))
    return camel_case(column.name)


@given(_tables())
def test_repeated_generation_is_byte_identical(table):
    first = generate_table_sources(table)
    second = generate_table_sources(table)

    assert first == second
    for first_file, second_file in zip(first.files, second.files):
        assert first_file.contents == second_file.contents


@given(_tables())
def test_field_order_matches_table_columns_declaration_order(table):
    context = build_entity_context(table, base_package="com.modelia.generated")

    expected_names = [_expected_field_name(column, table) for column in table.columns]
    assert [field.name for field in context.fields] == expected_names
    assert len(context.fields) == len(table.columns)


@given(_tables())
def test_imports_are_deduped_grouped_and_sorted(table):
    context = build_entity_context(table, base_package="com.modelia.generated")

    for group in context.import_groups:
        assert list(group) == sorted(set(group))
        assert len(group) == len(set(group))


@given(_tables())
def test_braces_and_parens_are_balanced_in_every_emitted_file(table):
    sources = generate_table_sources(table)

    for generated_file in sources.files:
        assert generated_file.contents.count("{") == generated_file.contents.count("}")
        assert generated_file.contents.count("(") == generated_file.contents.count(")")


@given(_enum_types())
def test_enum_source_generation_is_byte_identical(enum_type):
    first = generate_enum_source(enum_type, base_package="com.modelia.generated")
    second = generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert first == second
    assert first.contents == second.contents
