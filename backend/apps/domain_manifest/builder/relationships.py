"""Foreign key -> relationship mapping (design.md DD123, DD125)."""
from apps.spring_generator.emit.naming import camel_case, pascal_case, relationship_base_name


def _is_one_to_one(table, foreign_key) -> bool:
    # Restated locally on purpose (DD123): `emit.context._is_one_to_one` is private.
    return any(frozenset(unique.column_names) == frozenset(foreign_key.column_names) for unique in table.unique_constraints)


def build_relationships(table) -> list[dict]:
    relationships = []
    for foreign_key in table.foreign_keys:
        column = table.column_by_name(foreign_key.column_names[0])
        relationships.append(
            {
                "field": camel_case(relationship_base_name(column.name)),
                "attribute": camel_case(column.name),
                "column": column.name,
                "kind": "oneToOne" if _is_one_to_one(table, foreign_key) else "manyToOne",
                "target": pascal_case(foreign_key.referenced_table),
                "required": not column.nullable,
            }
        )
    return sorted(relationships, key=lambda relationship: relationship["field"])
