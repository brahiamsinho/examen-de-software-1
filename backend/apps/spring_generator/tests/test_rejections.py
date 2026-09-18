"""RED: apps.spring_generator.emit.errors does not exist yet.

Covers: the fixed DD15 rejection order (PK shape -> FK ->
discriminator -> enum), each named subclass, and that every named
error subclasses `UngeneratableTableError`. Identifier legality is
covered separately in `test_naming.py` (DD16).
"""
import pytest

from apps.relational_mapping.domain.schema import Column, ForeignKey, PrimaryKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.errors import (
    ForeignKeysUnsupportedError,
    InheritanceUnsupportedError,
    UngeneratableTableError,
    UnsupportedColumnTypeError,
    UnsupportedPrimaryKeyError,
)
from apps.spring_generator.emit.errors import reject_out_of_scope
from apps.spring_generator.tests.factories import a_column, a_table


def test_composite_primary_key_is_rejected():
    table = a_table(
        columns=(Column(name="id", type=ColumnType.UUID), Column(name="other_id", type=ColumnType.UUID)),
        primary_key=PrimaryKey(column_names=("id", "other_id"), name="pk_table"),
    )

    with pytest.raises(UnsupportedPrimaryKeyError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.table_name == table.name
    assert isinstance(excinfo.value, UngeneratableTableError)


def test_non_uuid_primary_key_is_rejected():
    table = a_table(
        columns=(Column(name="id", type=ColumnType.BIGINT),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_table"),
    )

    with pytest.raises(UnsupportedPrimaryKeyError):
        reject_out_of_scope(table)


def test_table_with_foreign_key_is_rejected():
    fk = ForeignKey(
        name="fk_product__category_id",
        column_names=("category_id",),
        referenced_table="category",
        referenced_column_names=("id",),
    )
    table = a_table(foreign_keys=(fk,))

    with pytest.raises(ForeignKeysUnsupportedError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.table_name == table.name
    assert excinfo.value.foreign_key_names == ("fk_product__category_id",)
    assert isinstance(excinfo.value, UngeneratableTableError)


def test_table_with_discriminator_column_is_rejected():
    table = a_table(discriminator_column="class_type")

    with pytest.raises(InheritanceUnsupportedError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.table_name == table.name
    assert excinfo.value.discriminator_column == "class_type"
    assert isinstance(excinfo.value, UngeneratableTableError)


def test_table_with_enum_column_is_rejected():
    table = a_table(columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status"),))

    with pytest.raises(UnsupportedColumnTypeError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.table_name == table.name
    assert excinfo.value.column_name == "status"
    assert excinfo.value.column_type == ColumnType.ENUM
    assert isinstance(excinfo.value, UngeneratableTableError)


def test_check_order_pk_before_foreign_key():
    fk = ForeignKey(
        name="fk_x", column_names=("category_id",), referenced_table="category", referenced_column_names=("id",)
    )
    table = a_table(
        columns=(Column(name="id", type=ColumnType.BIGINT),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_table"),
        foreign_keys=(fk,),
    )

    with pytest.raises(UnsupportedPrimaryKeyError):
        reject_out_of_scope(table)


def test_check_order_foreign_key_before_discriminator():
    fk = ForeignKey(
        name="fk_x", column_names=("category_id",), referenced_table="category", referenced_column_names=("id",)
    )
    table = a_table(foreign_keys=(fk,), discriminator_column="class_type")

    with pytest.raises(ForeignKeysUnsupportedError):
        reject_out_of_scope(table)


def test_check_order_discriminator_before_enum():
    table = a_table(
        columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status"),),
        discriminator_column="class_type",
    )

    with pytest.raises(InheritanceUnsupportedError):
        reject_out_of_scope(table)


def test_generatable_table_raises_nothing():
    table = a_table()

    assert reject_out_of_scope(table) is None
