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
    MalformedInheritanceTableError,
    UngeneratableSourceError,
    UngeneratableTableError,
    UnsupportedColumnTypeError,
    UnsupportedPrimaryKeyError,
)
from apps.spring_generator.emit.errors import reject_out_of_scope
from apps.spring_generator.tests.factories import a_column, a_table


def _vehicle_table(
    *,
    discriminator_values: dict | None = None,
    extra_columns: tuple[Column, ...] = (),
    foreign_keys: tuple[ForeignKey, ...] = (),
) -> Table:
    columns = (
        Column(name="id", type=ColumnType.UUID, nullable=False),
        Column(name="class_type", type=ColumnType.VARCHAR, nullable=False),
        Column(
            name="vin",
            type=ColumnType.VARCHAR,
            nullable=False,
            source_element_id="attr-vin",
            owning_class_id="vehicle",
        ),
        Column(
            name="door_count",
            type=ColumnType.INTEGER,
            nullable=True,
            source_element_id="attr-door-count",
            owning_class_id="car",
        ),
    )
    return Table(
        name="vehicle",
        columns=columns + extra_columns,
        primary_key=PrimaryKey(column_names=("id",), name="pk_vehicle"),
        foreign_keys=foreign_keys,
        source_class_ids=("vehicle", "car"),
        discriminator_column="class_type",
        discriminator_values=(
            {"vehicle": "VEHICLE", "car": "CAR"}
            if discriminator_values is None
            else discriminator_values
        ),
    )


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


def test_supported_discriminator_table_raises_nothing():
    table = _vehicle_table()

    assert reject_out_of_scope(table) is None


def test_discriminator_values_without_discriminator_column_are_malformed():
    table = a_table(discriminator_values={"vehicle": "VEHICLE"}, source_class_ids=("vehicle",))

    with pytest.raises(MalformedInheritanceTableError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.reason == "discriminator_column_required"
    assert excinfo.value.table_name == table.name


def test_discriminator_table_with_empty_source_class_ids_is_malformed():
    table = a_table(discriminator_column="class_type", discriminator_values={"vehicle": "VEHICLE"})

    with pytest.raises(MalformedInheritanceTableError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.reason == "source_class_ids_required"


def test_discriminator_table_missing_discriminator_column_in_columns_is_malformed():
    table = a_table(
        discriminator_column="kind",
        discriminator_values={"vehicle": "VEHICLE"},
        source_class_ids=("vehicle",),
    )

    with pytest.raises(MalformedInheritanceTableError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.reason == "discriminator_column_missing"
    assert excinfo.value.column_name == "kind"


def test_discriminator_table_missing_discriminator_value_is_malformed():
    table = _vehicle_table(discriminator_values={"vehicle": "VEHICLE"})

    with pytest.raises(MalformedInheritanceTableError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.reason == "discriminator_value_required"
    assert excinfo.value.class_id == "car"


def test_discriminator_table_with_owner_outside_hierarchy_is_malformed():
    table = _vehicle_table(
        extra_columns=(
            a_column(
                name="boat_code",
                type=ColumnType.VARCHAR,
                source_element_id="attr-boat-code",
                owning_class_id="boat",
            ),
        )
    )

    with pytest.raises(MalformedInheritanceTableError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.reason == "unknown_column_owner"
    assert excinfo.value.column_name == "boat_code"
    assert excinfo.value.class_id == "boat"


def test_discriminator_table_with_unowned_scalar_is_malformed():
    table = _vehicle_table(extra_columns=(a_column(name="legacy_code", type=ColumnType.VARCHAR),))

    with pytest.raises(MalformedInheritanceTableError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.reason == "unowned_column_unsupported"
    assert excinfo.value.column_name == "legacy_code"


def test_discriminator_table_with_subclass_owned_fk_is_malformed():
    fk = ForeignKey(
        name="fk_vehicle__garage_id",
        column_names=("garage_id",),
        referenced_table="garage",
        referenced_column_names=("id",),
    )
    table = _vehicle_table(
        extra_columns=(
            a_column(name="garage_id", type=ColumnType.UUID, nullable=True, owning_class_id="car"),
        ),
        foreign_keys=(fk,),
    )

    with pytest.raises(MalformedInheritanceTableError) as excinfo:
        reject_out_of_scope(table)

    assert excinfo.value.reason == "subclass_relationship_unsupported"
    assert excinfo.value.column_name == "garage_id"
    assert excinfo.value.class_id == "car"


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


def test_check_order_unnamed_enum_before_inheritance_shape():
    table = a_table(
        columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name=None),),
        discriminator_column="class_type",
    )

    with pytest.raises(UnsupportedColumnTypeError):
        reject_out_of_scope(table)


def test_generatable_table_raises_nothing():
    table = a_table()

    assert reject_out_of_scope(table) is None
