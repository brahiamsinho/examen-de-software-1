"""Typed rejection hierarchy for `Table` shapes this slice cannot emit
(design.md DD33-DD35), plus the fixed-order eager check that raises
them.

Mirrors `apps.relational_mapping.mapping.errors` (base + attribute-
carrying subclasses, defense-in-depth): a caller handing in a table
this slice cannot represent gets a named, catchable failure instead of
an entity that silently lost a relationship, and the check order is
deterministic for a table that violates several rules at once.
"""
from apps.relational_mapping.domain.schema import EnumType, Table
from apps.relational_mapping.domain.types import ColumnType


class UngeneratableSourceError(Exception):
    """Root for every error this app's `reject_*` functions raise (DD33)."""


class UngeneratableTableError(UngeneratableSourceError):
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


class CompositeForeignKeyUnsupportedError(UngeneratableTableError):
    def __init__(self, table_name: str, foreign_key_name: str, column_names: tuple[str, ...]):
        self.table_name = table_name
        self.foreign_key_name = foreign_key_name
        self.column_names = tuple(column_names)
        super().__init__(
            "Table {!r} has an unsupported composite foreign key {!r}: {!r}".format(
                table_name, foreign_key_name, self.column_names
            )
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


class InvalidJavaIdentifierError(UngeneratableSourceError):
    def __init__(self, source_name: str, converted: str):
        self.source_name = source_name
        self.converted = converted
        super().__init__(
            "Name {!r} does not convert to a legal Java identifier: {!r}".format(source_name, converted)
        )


class InvalidResourcePathError(UngeneratableTableError):
    def __init__(self, table_name: str, segment: str):
        self.table_name = table_name
        self.segment = segment
        super().__init__(
            "Table {!r} yields an invalid resource path segment {!r}".format(table_name, segment)
        )


class UngeneratableEnumError(UngeneratableSourceError):
    """Base for every error `reject_ungeneratable_enum` raises (DD33)."""


class EmptyEnumTypeError(UngeneratableEnumError):
    def __init__(self, enum_type_name: str):
        self.enum_type_name = enum_type_name
        super().__init__("EnumType {!r} has no labels".format(enum_type_name))


class DuplicateEnumConstantError(UngeneratableEnumError):
    def __init__(self, enum_type_name: str, constant: str, labels: tuple[str, ...]):
        self.enum_type_name = enum_type_name
        self.constant = constant
        self.labels = tuple(labels)
        super().__init__(
            "EnumType {!r} labels {!r} collide on constant {!r}".format(
                enum_type_name, self.labels, constant
            )
        )


def reject_out_of_scope(table: Table) -> None:
    """DD35's fixed check order: PK shape -> composite FK (first
    offender in `foreign_keys` order) -> discriminator -> unnamed enum
    column (first offender in `columns` order). Raises the first
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

    for foreign_key in table.foreign_keys:
        if len(foreign_key.column_names) > 1:
            raise CompositeForeignKeyUnsupportedError(
                table_name=table.name,
                foreign_key_name=foreign_key.name,
                column_names=foreign_key.column_names,
            )

    if table.discriminator_column is not None or table.discriminator_values:
        raise InheritanceUnsupportedError(
            table_name=table.name, discriminator_column=table.discriminator_column
        )

    for column in table.columns:
        if column.type is ColumnType.ENUM and column.enum_type_name is None:
            raise UnsupportedColumnTypeError(
                table_name=table.name, column_name=column.name, column_type=column.type
            )


def reject_invalid_resource_path(table: Table) -> None:
    """DD45's fifth check, run after `reject_out_of_scope`'s four
    (DD35): `naming.resource_path_segment(table.name)` must satisfy its
    own `^[a-z0-9]+(-[a-z0-9]+)*$` whitelist. Raises nothing for a
    table whose resource path segment is legal.
    """
    # Deferred import: naming.py imports this module's
    # InvalidResourcePathError, so a module-level import here would
    # create a cycle.
    from apps.spring_generator.emit.naming import resource_path_segment

    resource_path_segment(table.name)


def reject_ungeneratable_enum(enum_type: EnumType) -> None:
    """DD33's fixed check order: empty labels -> duplicate constant
    (first offender, in `labels` order). Raises the first violated
    rule; raises nothing for a generatable `EnumType`.
    """
    if not enum_type.labels:
        raise EmptyEnumTypeError(enum_type_name=enum_type.name)

    # Deferred import: naming.py imports this module's
    # InvalidJavaIdentifierError, so a module-level import here would
    # create a cycle.
    from apps.spring_generator.emit.naming import screaming_snake_case

    seen_constants: set[str] = set()
    for label in enum_type.labels:
        constant = screaming_snake_case(label)
        if constant in seen_constants:
            raise DuplicateEnumConstantError(
                enum_type_name=enum_type.name, constant=constant, labels=enum_type.labels
            )
        seen_constants.add(constant)
