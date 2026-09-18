"""RED: apps.relational_mapping.domain.schema does not exist yet.

Covers: frozen-dataclass shapes, field defaults, `table_by_name`/
`column_by_name`, mutation raises, and the "zero framework imports"
scenario (relational-mapping spec, Requirement: RelationalModel Domain
Structure).
"""
import ast
import dataclasses
import inspect

import pytest

from apps.relational_mapping.domain import schema, types
from apps.relational_mapping.domain.schema import (
    Column,
    EnumType,
    ForeignKey,
    Index,
    PrimaryKey,
    RelationalModel,
    Table,
    UniqueConstraint,
)
from apps.relational_mapping.domain.types import ColumnType, ReferentialAction

_FORBIDDEN_IMPORT_PREFIXES = ("django", "psycopg", "sqlite3", "MySQLdb", "java", "org.springframework")


def _imported_module_names(module) -> list[str]:
    tree = ast.parse(inspect.getsource(module))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_domain_module_has_zero_framework_imports():
    for module in (types, schema):
        for imported_name in _imported_module_names(module):
            assert not imported_name.startswith(_FORBIDDEN_IMPORT_PREFIXES), (
                f"{module.__name__} imports forbidden module {imported_name!r}"
            )


def test_column_defaults():
    column = Column(name="total", type=ColumnType.NUMERIC)

    assert column.nullable is False
    assert column.length is None
    assert column.precision is None
    assert column.scale is None
    assert column.enum_type_name is None
    assert column.source_element_id is None


def test_column_is_frozen():
    column = Column(name="total", type=ColumnType.NUMERIC)

    with pytest.raises(dataclasses.FrozenInstanceError):
        column.name = "other"


def test_foreign_key_defaults():
    fk = ForeignKey(
        name="fk_order__customer_id",
        column_names=("customer_id",),
        referenced_table="customer",
        referenced_column_names=("id",),
    )

    assert fk.on_delete is ReferentialAction.NO_ACTION
    assert fk.on_update is ReferentialAction.NO_ACTION
    assert fk.source_relationship_id is None


def test_table_column_by_name_finds_existing_column():
    id_column = Column(name="id", type=ColumnType.UUID)
    total_column = Column(name="total", type=ColumnType.NUMERIC)
    table = Table(
        name="order",
        columns=(id_column, total_column),
        primary_key=PrimaryKey(column_names=("id",), name="pk_order"),
    )

    assert table.column_by_name("total") is total_column
    assert table.column_by_name("missing") is None


def test_table_defaults():
    table = Table(
        name="order",
        columns=(Column(name="id", type=ColumnType.UUID),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_order"),
    )

    assert table.foreign_keys == ()
    assert table.unique_constraints == ()
    assert table.indexes == ()
    assert table.source_class_ids == ()
    assert table.discriminator_column is None
    assert dict(table.discriminator_values) == {}


def test_table_is_frozen():
    table = Table(
        name="order",
        columns=(Column(name="id", type=ColumnType.UUID),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_order"),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        table.name = "renamed"


def test_relational_model_table_by_name_and_enum_type_by_name():
    order_table = Table(
        name="order",
        columns=(Column(name="id", type=ColumnType.UUID),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_order"),
    )
    status_enum = EnumType(name="order_status", labels=("DRAFT", "PAID"))
    model = RelationalModel(tables=(order_table,), enum_types=(status_enum,))

    assert model.table_by_name("order") is order_table
    assert model.table_by_name("missing") is None
    assert model.enum_type_by_name("order_status") is status_enum
    assert model.enum_type_by_name("missing") is None


def test_relational_model_defaults_to_empty():
    model = RelationalModel()

    assert model.tables == ()
    assert model.enum_types == ()


def test_unique_constraint_and_index_shapes():
    unique = UniqueConstraint(name="uq_order__number", column_names=("number",))
    index = Index(name="ix_order__customer_id", column_names=("customer_id",))

    assert unique.column_names == ("number",)
    assert index.unique is False
