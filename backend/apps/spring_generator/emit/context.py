"""Builds frozen `EntityContext`/`RepositoryContext` template contexts
(design.md DD9-DD12). All branching over `ColumnType`, annotation
choice, and import selection lives here so `emit/templates/*.java.j2`
stay purely data-driven (DD2, DD13).

Per the DD14 guard, string assembly in this module uses only `.format()`
and reassignment loops — never `+`/`str.join`/`%`/f-string concatenation
of the generator's own Python source.
"""
from dataclasses import dataclass

from apps.relational_mapping.domain.schema import Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.javatypes import java_type_for
from apps.spring_generator.emit.naming import camel_case, pascal_case

_ENTITY_FIXED_IMPORTS = (
    "jakarta.persistence.Column",
    "jakarta.persistence.Entity",
    "jakarta.persistence.GeneratedValue",
    "jakarta.persistence.GenerationType",
    "jakarta.persistence.Id",
    "jakarta.persistence.Table",
)


@dataclass(frozen=True)
class FieldContext:
    name: str                          # camelCase Java identifier (DD16)
    java_type: str                     # simple type name
    getter: str
    setter: str
    annotations: tuple[str, ...]       # fixed order: @Id, @GeneratedValue, @Column, @NotNull, @Size (DD11)


@dataclass(frozen=True)
class EntityContext:
    package: str
    class_name: str
    table_name: str
    fields: tuple[FieldContext, ...]
    import_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class RepositoryContext:
    package: str
    class_name: str
    repository_name: str
    import_groups: tuple[tuple[str, ...], ...]


def _comma_join(parts: list[str]) -> str:
    """Comma-space join without `str.join` (DD14 guard)."""
    joined = ""
    for index, part in enumerate(parts):
        joined = part if index == 0 else "{}, {}".format(joined, part)
    return joined


def _group_imports(base_package: str, fqns: set[str]) -> tuple[tuple[str, ...], ...]:
    """DD12: fixed group order (`java.*`, `jakarta.*`, `org.*`,
    `<base_package>.*`), lexicographic within each group. `set`
    iteration is the only unordered step in this module, so this is
    the only place that needs an explicit ordering rule.
    """
    prefixes = ("java.", "jakarta.", "org.", "{}.".format(base_package))
    groups: list[tuple[str, ...]] = []
    remaining = set(fqns)
    for prefix in prefixes:
        matched = sorted(fqn for fqn in remaining if fqn.startswith(prefix))
        remaining -= set(matched)
        if matched:
            groups.append(tuple(matched))
    return tuple(groups)


def _column_annotation(column, *, is_primary_key: bool) -> str:
    """DD10: explicit `name` always first, then only present attributes,
    in the fixed order `name, nullable, length, precision, scale,
    columnDefinition, updatable`.
    """
    parts = ['name = "{}"'.format(column.name)]
    nullable_literal = "false" if (is_primary_key or not column.nullable) else "true"
    parts.append("nullable = {}".format(nullable_literal))
    if column.length is not None:
        parts.append("length = {}".format(column.length))
    if column.precision is not None:
        parts.append("precision = {}".format(column.precision))
    if column.scale is not None:
        parts.append("scale = {}".format(column.scale))
    if column.type is ColumnType.TEXT:
        parts.append('columnDefinition = "TEXT"')
    if is_primary_key:
        parts.append("updatable = false")
    return "@Column({})".format(_comma_join(parts))


def _field_context(column, *, is_primary_key: bool) -> FieldContext:
    field_name = camel_case(column.name)
    java_type = java_type_for(column.type)
    pascal_name = pascal_case(column.name)

    annotations: list[str] = []
    if is_primary_key:
        annotations.append("@Id")
        annotations.append("@GeneratedValue(strategy = GenerationType.UUID)")
        annotations.append(_column_annotation(column, is_primary_key=True))
        # DD8: no @NotNull on the PK — Bean Validation would fire before
        # the provider generates the id on persist().
    else:
        annotations.append(_column_annotation(column, is_primary_key=False))
        if not column.nullable:
            annotations.append("@NotNull")
        if column.type is ColumnType.VARCHAR and column.length is not None:
            annotations.append("@Size(max = {})".format(column.length))

    return FieldContext(
        name=field_name,
        java_type=java_type.name,
        getter="get{}".format(pascal_name),
        setter="set{}".format(pascal_name),
        annotations=tuple(annotations),
    )


def build_entity_context(table: Table, *, base_package: str) -> EntityContext:
    pk_column_name = table.primary_key.column_names[0]
    field_contexts: list[FieldContext] = []
    type_imports: set[str] = set()
    uses_not_null = False
    uses_size = False

    for column in table.columns:
        is_primary_key = column.name == pk_column_name
        field_contexts.append(_field_context(column, is_primary_key=is_primary_key))

        java_type = java_type_for(column.type)
        if java_type.import_fqn is not None:
            type_imports.add(java_type.import_fqn)

        if not is_primary_key and not column.nullable:
            uses_not_null = True
        if not is_primary_key and column.type is ColumnType.VARCHAR and column.length is not None:
            uses_size = True

    all_imports = set(_ENTITY_FIXED_IMPORTS) | type_imports
    if uses_not_null:
        all_imports.add("jakarta.validation.constraints.NotNull")
    if uses_size:
        all_imports.add("jakarta.validation.constraints.Size")

    return EntityContext(
        package="{}.domain".format(base_package),
        class_name=pascal_case(table.name),
        table_name=table.name,
        fields=tuple(field_contexts),
        import_groups=_group_imports(base_package, all_imports),
    )


def build_repository_context(table: Table, *, base_package: str) -> RepositoryContext:
    entity_class_name = pascal_case(table.name)
    imports = {
        "org.springframework.data.jpa.repository.JpaRepository",
        "java.util.UUID",
        "{}.domain.{}".format(base_package, entity_class_name),
    }

    return RepositoryContext(
        package="{}.persistence".format(base_package),
        class_name=entity_class_name,
        repository_name="{}Repository".format(entity_class_name),
        import_groups=_group_imports(base_package, imports),
    )
