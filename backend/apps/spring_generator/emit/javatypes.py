"""Deterministic `ColumnType` -> Java type mapping (design.md DD5-DD7).

Boxed types only, never primitives (DD5): a primitive cannot represent
`nullable=True`, so the mapping is a pure function of `ColumnType`
alone, independent of nullability. `TIMESTAMPTZ -> OffsetDateTime`
(DD6) round-trips the source column's timezone offset; `TEXT`'s
`columnDefinition = "TEXT"` annotation (DD7) is built in `context.py`,
not here — this module only owns the type/import pair.
"""
from dataclasses import dataclass

from apps.relational_mapping.domain.types import ColumnType


@dataclass(frozen=True)
class JavaType:
    name: str                  # simple name used in the field declaration
    import_fqn: str | None     # None for java.lang types, which need no import


_JAVA_TYPE_BY_COLUMN_TYPE: dict[ColumnType, JavaType] = {
    ColumnType.UUID: JavaType(name="UUID", import_fqn="java.util.UUID"),
    ColumnType.VARCHAR: JavaType(name="String", import_fqn=None),
    ColumnType.TEXT: JavaType(name="String", import_fqn=None),
    ColumnType.INTEGER: JavaType(name="Integer", import_fqn=None),
    ColumnType.BIGINT: JavaType(name="Long", import_fqn=None),
    ColumnType.NUMERIC: JavaType(name="BigDecimal", import_fqn="java.math.BigDecimal"),
    ColumnType.BOOLEAN: JavaType(name="Boolean", import_fqn=None),
    ColumnType.DATE: JavaType(name="LocalDate", import_fqn="java.time.LocalDate"),
    ColumnType.TIMESTAMPTZ: JavaType(name="OffsetDateTime", import_fqn="java.time.OffsetDateTime"),
}


def java_type_for(column_type: ColumnType) -> JavaType:
    """Every non-`ENUM` `ColumnType` maps to exactly one `JavaType`.
    A `Column` with `enum_type_name` set never reaches this function —
    `emit.context` resolves its Java type via `pascal_case(enum_type_name)`
    instead. `ColumnType.ENUM` with no `enum_type_name` still reaches
    `emit.errors.reject_out_of_scope` and is rejected before this function
    is called.
    """
    return _JAVA_TYPE_BY_COLUMN_TYPE[column_type]
