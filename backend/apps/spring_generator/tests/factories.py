"""Test factories for `spring_generator` scenarios (design.md DD22).

Imports only `apps.relational_mapping.domain` — never
`apps.relational_mapping.tests.factories` (`backend/apps/README.md`
no-cross-imports convention: a cross-app *test-package* dependency is
the same coupling a cross-app production import would be). Generator
scenarios need `Table`-shaped builders directly, not
`CanonicalUmlModel`-shaped ones.
"""
from apps.relational_mapping.domain.schema import Column, EnumType, ForeignKey, PrimaryKey, Table, UniqueConstraint
from apps.relational_mapping.domain.types import ColumnType


def a_column(
    *,
    name: str = "name",
    type: ColumnType = ColumnType.VARCHAR,
    nullable: bool = False,
    length: int | None = None,
    precision: int | None = None,
    scale: int | None = None,
    enum_type_name: str | None = None,
) -> Column:
    return Column(
        name=name,
        type=type,
        nullable=nullable,
        length=length,
        precision=precision,
        scale=scale,
        enum_type_name=enum_type_name,
    )


def a_primary_key(*, column_names: tuple[str, ...] = ("id",), name: str | None = "pk_table") -> PrimaryKey:
    return PrimaryKey(column_names=column_names, name=name)


def a_foreign_key(
    *,
    name: str = "fk_product__category_id",
    column_names: tuple[str, ...] = ("category_id",),
    referenced_table: str = "category",
    referenced_column_names: tuple[str, ...] = ("id",),
) -> ForeignKey:
    return ForeignKey(
        name=name,
        column_names=column_names,
        referenced_table=referenced_table,
        referenced_column_names=referenced_column_names,
    )


def a_unique_constraint(
    *, name: str = "uq_product__category_id", column_names: tuple[str, ...] = ("category_id",)
) -> UniqueConstraint:
    return UniqueConstraint(name=name, column_names=column_names)


def an_enum_type(*, name: str = "order_status", labels: tuple[str, ...] = ("PENDING", "PAID", "SHIPPED")) -> EnumType:
    return EnumType(name=name, labels=labels)


def a_table(
    *,
    name: str = "product",
    columns: tuple[Column, ...] | None = None,
    primary_key: PrimaryKey | None = None,
    foreign_keys: tuple = (),
    unique_constraints: tuple = (),
    discriminator_column: str | None = None,
) -> Table:
    """A minimal generatable table: UUID PK named `id` plus any extra
    scalar columns. Callers needing an out-of-scope shape (composite
    FK, discriminator, unnamed-enum column, non-UUID/composite PK)
    override the relevant keyword explicitly.
    """
    resolved_columns = columns if columns is not None else (a_column(name="name", type=ColumnType.VARCHAR),)
    if not any(column.name == "id" for column in resolved_columns):
        resolved_columns = (Column(name="id", type=ColumnType.UUID, nullable=False),) + resolved_columns

    return Table(
        name=name,
        columns=resolved_columns,
        primary_key=primary_key if primary_key is not None else a_primary_key(),
        foreign_keys=foreign_keys,
        unique_constraints=unique_constraints,
        discriminator_column=discriminator_column,
    )
