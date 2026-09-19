"""RED->GREEN: fixed DD35 rejection order (PK shape -> composite FK ->
discriminator -> unnamed ENUM), each named subclass, and that every
named table error subclasses both `UngeneratableTableError` and the
new `UngeneratableSourceError` root (DD33). A single-column FK and a
named enum column are no longer rejected (DD35) — they are covered as
generatable shapes here and generated in full by
`test_relationship_fields.py` / `test_enum_fields.py`.

Identifier legality is covered separately in `test_naming.py` (DD16).
"""
import pytest

from apps.relational_mapping.domain.schema import Column, ForeignKey, PrimaryKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.errors import (
    CompositeForeignKeyUnsupportedError,
    InheritanceUnsupportedError,
    UngeneratableSourceError,
    UngeneratableTableError,
    UnsupportedColumnTypeError,
    UnsupportedPrimaryKeyError,
)
from apps.spring_generator.emit.errors import reject_out_of_scope
from apps.spring_generator.emit.renderer import generate_table_sources
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
    assert isinstance(excinfo.value, UngeneratableSourceError)


def test_non_uuid_primary_key_is_rejected():
    table = a_table(
        columns=(Column(name="id", type=ColumnType.BIGINT),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_table"),
    )

    with pytest.raises(UnsupportedPrimaryKeyError):
        reject_out_of_scope(table)


def test_table_with_composite_foreign_key_is_rejected():
    fk = ForeignKey(
        name="fk_product__category",
        column_names=("category_id", "category_region"),
        referenced_table="category",
        referenced_column_names=("id", "region"),
    )
    table = a_table(foreign_keys=(fk,))

    with pytest.raises(CompositeForeignKeyUnsupportedError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.table_name == table.name
    assert excinfo.value.foreign_key_name == "fk_product__category"
    assert excinfo.value.column_names == ("category_id", "category_region")
    assert isinstance(excinfo.value, UngeneratableTableError)
    assert isinstance(excinfo.value, UngeneratableSourceError)


def test_composite_foreign_key_rejection_reports_first_offender():
    single_fk = ForeignKey(
        name="fk_single", column_names=("owner_id",), referenced_table="owner", referenced_column_names=("id",)
    )
    composite_fk = ForeignKey(
        name="fk_composite",
        column_names=("category_id", "category_region"),
        referenced_table="category",
        referenced_column_names=("id", "region"),
    )
    table = a_table(foreign_keys=(single_fk, composite_fk))

    with pytest.raises(CompositeForeignKeyUnsupportedError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.foreign_key_name == "fk_composite"


def test_table_with_single_column_foreign_key_raises_nothing():
    fk = ForeignKey(
        name="fk_product__category_id",
        column_names=("category_id",),
        referenced_table="category",
        referenced_column_names=("id",),
    )
    table = a_table(foreign_keys=(fk,))

    assert reject_out_of_scope(table) is None


def test_table_with_discriminator_column_is_rejected():
    table = a_table(discriminator_column="class_type")

    with pytest.raises(InheritanceUnsupportedError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.table_name == table.name
    assert excinfo.value.discriminator_column == "class_type"
    assert isinstance(excinfo.value, UngeneratableTableError)
    assert isinstance(excinfo.value, UngeneratableSourceError)


def test_discriminator_table_with_owned_attribute_column_is_still_rejected_before_rendering():
    table = a_table(
        columns=(
            Column(name="id", type=ColumnType.UUID),
            Column(
                name="vin",
                type=ColumnType.VARCHAR,
                source_element_id="attr-vin",
                owning_class_id="class-vehicle",
            ),
        ),
        discriminator_column="class_type",
    )

    with pytest.raises(InheritanceUnsupportedError) as excinfo:
        generate_table_sources(table)

    assert excinfo.value.table_name == table.name
    assert excinfo.value.discriminator_column == "class_type"


def test_table_with_unnamed_enum_column_is_rejected():
    table = a_table(columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name=None),))

    with pytest.raises(UnsupportedColumnTypeError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.table_name == table.name
    assert excinfo.value.column_name == "status"
    assert excinfo.value.column_type == ColumnType.ENUM
    assert isinstance(excinfo.value, UngeneratableTableError)
    assert isinstance(excinfo.value, UngeneratableSourceError)


def test_table_with_named_enum_column_raises_nothing():
    table = a_table(columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status"),))

    assert reject_out_of_scope(table) is None


def test_check_order_pk_before_composite_foreign_key():
    fk = ForeignKey(
        name="fk_x",
        column_names=("category_id", "category_region"),
        referenced_table="category",
        referenced_column_names=("id", "region"),
    )
    table = a_table(
        columns=(Column(name="id", type=ColumnType.BIGINT),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_table"),
        foreign_keys=(fk,),
    )

    with pytest.raises(UnsupportedPrimaryKeyError):
        reject_out_of_scope(table)


def test_check_order_composite_foreign_key_before_discriminator():
    fk = ForeignKey(
        name="fk_x",
        column_names=("category_id", "category_region"),
        referenced_table="category",
        referenced_column_names=("id", "region"),
    )
    table = a_table(foreign_keys=(fk,), discriminator_column="class_type")

    with pytest.raises(CompositeForeignKeyUnsupportedError):
        reject_out_of_scope(table)


def test_check_order_discriminator_before_unnamed_enum():
    table = a_table(
        columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name=None),),
        discriminator_column="class_type",
    )

    with pytest.raises(InheritanceUnsupportedError):
        reject_out_of_scope(table)


def test_generatable_table_raises_nothing():
    table = a_table()

    assert reject_out_of_scope(table) is None
