"""Property tests for the spec's determinism criterion (design.md DD12):
(a) repeated calls are byte-identical, (b) field order == `table.columns`
declaration order, (c) imports deduped/grouped/sorted, (d) braces and
parens balanced in every emitted file.
"""
from hypothesis import given, strategies as st

from apps.relational_mapping.domain.schema import Column, PrimaryKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_entity_context
from apps.spring_generator.emit.naming import camel_case
from apps.spring_generator.emit.renderer import generate_table_sources

_TABLE_NAMES = ["product", "order_item", "customer", "invoice"]
_COLUMN_NAMES = ["name", "description", "quantity", "amount", "notes", "active"]
_NON_ENUM_TYPES = [column_type for column_type in ColumnType if column_type is not ColumnType.ENUM]


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
def _tables(draw):
    table_name = draw(st.sampled_from(_TABLE_NAMES))
    extra_columns = draw(_extra_columns())
    columns = (Column(name="id", type=ColumnType.UUID, nullable=False),) + extra_columns
    return Table(
        name=table_name, columns=columns, primary_key=PrimaryKey(column_names=("id",), name=f"pk_{table_name}")
    )


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

    expected_names = [camel_case(column.name) for column in table.columns]
    assert [field.name for field in context.fields] == expected_names


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
