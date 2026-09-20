"""Column -> attribute mapping (design.md DD125).

The type map is keyed on the `ColumnType` member *name* so this module needs no
import from `apps.relational_mapping` (DD123: `emit.naming` is the only shared
module). An unknown member raises `ValueError` rather than guessing a type.
"""
from apps.spring_generator.emit.naming import camel_case, pascal_case

_NEUTRAL_TYPES = {
    "UUID": "uuid",
    "VARCHAR": "string",
    "TEXT": "text",
    "INTEGER": "integer",
    "BIGINT": "long",
    "NUMERIC": "decimal",
    "BOOLEAN": "boolean",
    "DATE": "date",
    "TIMESTAMPTZ": "datetime",
    "ENUM": "enum",
}


def neutral_type(column_type) -> str:
    try:
        return _NEUTRAL_TYPES[column_type.name]
    except KeyError:
        raise ValueError(f"unsupported column type {column_type.name!r}") from None


def _subtype(table, column) -> str | None:
    root_class_id = table.source_class_ids[0] if table.source_class_ids else None
    if column.owning_class_id is None or column.owning_class_id == root_class_id:
        return None
    owner = table.discriminator_values.get(column.owning_class_id)
    return pascal_case(owner) if owner else None


def _attribute(table, column) -> dict:
    return {
        "name": camel_case(column.name),
        "column": column.name,
        "type": neutral_type(column.type),
        "required": not column.nullable,
        "primaryKey": column.name == table.primary_key.column_names[0],
        "maxLength": column.length if column.type.name == "VARCHAR" else None,
        "enum": pascal_case(column.enum_type_name) if column.enum_type_name else None,
        "subtype": _subtype(table, column),
    }


def build_attributes(table) -> list[dict]:
    return [_attribute(table, column) for column in table.columns if column.name != table.discriminator_column]
