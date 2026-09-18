"""RED: apps.spring_generator.emit.javatypes does not exist yet.

Covers: all 9 supported `ColumnType` rows map to a Java type + import
(design.md DD5-DD7 table), including `TIMESTAMPTZ -> OffsetDateTime`
(DD6) and `TEXT -> String` (DD7's `columnDefinition` lives in
`context.py`, not here). Boxed types only, never primitives (DD5).
"""
import pytest

from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.javatypes import JavaType, java_type_for

_EXPECTED = {
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


@pytest.mark.parametrize("column_type", list(_EXPECTED))
def test_java_type_for_maps_every_supported_column_type(column_type):
    assert java_type_for(column_type) == _EXPECTED[column_type]


def test_java_types_are_never_primitives():
    for column_type in _EXPECTED:
        java_type = java_type_for(column_type)
        assert java_type.name[0].isupper(), f"{column_type} mapped to a primitive-looking name"


def test_java_type_is_frozen():
    import dataclasses

    java_type = java_type_for(ColumnType.VARCHAR)

    with pytest.raises(dataclasses.FrozenInstanceError):
        java_type.name = "other"
