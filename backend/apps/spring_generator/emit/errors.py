"""Typed rejection hierarchy for `Table` shapes this slice cannot emit
(design.md DD15), plus the fixed-order eager check that raises them.

Mirrors `apps.relational_mapping.mapping.errors` (base + attribute-
carrying subclasses, defense-in-depth): a caller handing in a table
this slice cannot represent gets a named, catchable failure instead of
an entity that silently lost a relationship, and the check order is
deterministic for a table that violates several rules at once.
"""
from apps.relational_mapping.domain.schema import Table
from apps.relational_mapping.domain.types import ColumnType


class UngeneratableTableError(Exception):
    """Base for every error `reject_out_of_scope` raises."""


class UnsupportedPrimaryKeyError(UngeneratableTableError):
    def __init__(self, table_name: str, column_names: tuple[str, ...], reason: str):
        self.table_name = table_name
        self.column_names = tuple(column_names)
        self.reason = reason
        super().__init__(
            "Table {!r} has an unsupported primary key {!r}: {!r}".format(
                table_name, self.column_names, reason
            )
        )


class ForeignKeysUnsupportedError(UngeneratableTableError):
    def __init__(self, table_name: str, foreign_key_names: tuple[str, ...]):
        self.table_name = table_name
        self.foreign_key_names = tuple(foreign_key_names)
        super().__init__(
            "Table {!r} has unsupported foreign keys: {!r}".format(table_name, self.foreign_key_names)
        )


class InheritanceUnsupportedError(UngeneratableTableError):
    def __init__(self, table_name: str, discriminator_column: str | None):
        self.table_name = table_name
        self.discriminator_column = discriminator_column
        super().__init__(
            "Table {!r} has unsupported inheritance discriminator {!r}".format(
                table_name, discriminator_column
            )
        )


class UnsupportedColumnTypeError(UngeneratableTableError):
    def __init__(self, table_name: str, column_name: str, column_type: ColumnType):
        self.table_name = table_name
        self.column_name = column_name
        self.column_type = column_type
        super().__init__(
            "Table {!r} column {!r} has unsupported type {!r}".format(
                table_name, column_name, column_type
            )
        )


class InvalidJavaIdentifierError(UngeneratableTableError):
    def __init__(self, source_name: str, converted: str):
        self.source_name = source_name
        self.converted = converted
        super().__init__(
            "Name {!r} does not convert to a legal Java identifier: {!r}".format(source_name, converted)
        )


def reject_out_of_scope(table: Table) -> None:
    """DD15's fixed check order: PK shape -> FK -> discriminator ->
    enum column (first offender in `columns` order). Raises the first
    violated rule; raises nothing for a generatable table.
    """
    primary_key = table.primary_key
    pk_column = table.column_by_name(primary_key.column_names[0]) if len(primary_key.column_names) == 1 else None
    if len(primary_key.column_names) != 1 or pk_column is None or pk_column.type is not ColumnType.UUID:
        raise UnsupportedPrimaryKeyError(
            table_name=table.name,
            column_names=primary_key.column_names,
            reason="primary key must be exactly one UUID column",
        )

    if table.foreign_keys:
        raise ForeignKeysUnsupportedError(
            table_name=table.name,
            foreign_key_names=tuple(fk.name for fk in table.foreign_keys),
        )

    if table.discriminator_column is not None or table.discriminator_values:
        raise InheritanceUnsupportedError(
            table_name=table.name, discriminator_column=table.discriminator_column
        )

    for column in table.columns:
        if column.type is ColumnType.ENUM:
            raise UnsupportedColumnTypeError(
                table_name=table.name, column_name=column.name, column_type=column.type
            )
