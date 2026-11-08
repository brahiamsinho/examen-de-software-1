"""Read-only serialisation of the authoritative relational model.

The preview deliberately consumes ``RelationalModel`` rather than UML so its
tables and SQL cannot diverge from backend generation.
"""
from apps.relational_mapping.domain.schema import Column, RelationalModel


def _column_type(column: Column) -> str:
    if column.type == "VARCHAR":
        return f"VARCHAR({column.length})"
    if column.type == "NUMERIC":
        return f"NUMERIC({column.precision}, {column.scale})"
    if column.type == "ENUM":
        assert column.enum_type_name is not None
        return column.enum_type_name
    return str(column.type)


def relational_preview(model: RelationalModel) -> dict:
    """Return JSON-ready relational structures in mapper-defined order."""
    return {
        "tables": [
            {
                "name": table.name,
                "columns": [
                    {
                        "name": column.name,
                        "type": _column_type(column),
                        "nullable": column.nullable,
                        "primary_key": column.name in table.primary_key.column_names,
                    }
                    for column in table.columns
                ],
                "foreign_keys": [
                    {
                        "name": foreign_key.name,
                        "columns": list(foreign_key.column_names),
                        "referenced_table": foreign_key.referenced_table,
                        "referenced_columns": list(foreign_key.referenced_column_names),
                        "on_delete": str(foreign_key.on_delete),
                        "on_update": str(foreign_key.on_update),
                        "relationship_id": str(foreign_key.source_relationship_id)
                        if foreign_key.source_relationship_id is not None
                        else None,
                    }
                    for foreign_key in table.foreign_keys
                ],
            }
            for table in model.tables
        ]
    }


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_type(column: Column) -> str:
    if column.type == "VARCHAR":
        return f"VARCHAR({column.length})"
    if column.type == "NUMERIC":
        return f"NUMERIC({column.precision}, {column.scale})"
    if column.type == "ENUM":
        assert column.enum_type_name is not None
        return _quote_identifier(column.enum_type_name)
    return str(column.type)


def relational_sql(model: RelationalModel) -> str:
    """Render deterministic PostgreSQL DDL without executing it.

    Tables are emitted before foreign keys. This makes self-references and
    cyclic associations valid while preserving every ordering decision already
    made by the mapper.
    """
    statements: list[str] = []
    for enum_type in model.enum_types:
        labels = ", ".join(_quote_literal(label) for label in enum_type.labels)
        statements.append(f"CREATE TYPE {_quote_identifier(enum_type.name)} AS ENUM ({labels});")

    for table in model.tables:
        definitions = [
            " ".join(
                part
                for part in (
                    _quote_identifier(column.name),
                    _sql_type(column),
                    None if column.nullable else "NOT NULL",
                )
                if part is not None
            )
            for column in table.columns
        ]
        primary_key_columns = ", ".join(_quote_identifier(name) for name in table.primary_key.column_names)
        definitions.append(
            f"CONSTRAINT {_quote_identifier(table.primary_key.name or f'pk_{table.name}')} "
            f"PRIMARY KEY ({primary_key_columns})"
        )
        for constraint in table.unique_constraints:
            columns = ", ".join(_quote_identifier(name) for name in constraint.column_names)
            definitions.append(f"CONSTRAINT {_quote_identifier(constraint.name)} UNIQUE ({columns})")
        body = ",\n  ".join(definitions)
        statements.append(f"CREATE TABLE {_quote_identifier(table.name)} (\n  {body}\n);")

    for table in model.tables:
        for foreign_key in table.foreign_keys:
            columns = ", ".join(_quote_identifier(name) for name in foreign_key.column_names)
            referenced_columns = ", ".join(
                _quote_identifier(name) for name in foreign_key.referenced_column_names
            )
            statements.append(
                f"ALTER TABLE {_quote_identifier(table.name)} ADD CONSTRAINT {_quote_identifier(foreign_key.name)} "
                f"FOREIGN KEY ({columns}) REFERENCES {_quote_identifier(foreign_key.referenced_table)} "
                f"({referenced_columns}) ON DELETE {foreign_key.on_delete} ON UPDATE {foreign_key.on_update};"
            )

    for table in model.tables:
        for index in table.indexes:
            columns = ", ".join(_quote_identifier(name) for name in index.column_names)
            unique = "UNIQUE " if index.unique else ""
            statements.append(
                f"CREATE {unique}INDEX {_quote_identifier(index.name)} ON {_quote_identifier(table.name)} ({columns});"
            )
    return "\n\n".join(statements) + ("\n" if statements else "")
