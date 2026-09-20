"""Inheritance-specific contexts for discriminator-backed Single Table generation."""
from dataclasses import dataclass

from apps.relational_mapping.domain.schema import ForeignKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import (
    FieldContext,
    RepositoryContext,
    _field_context,
    _group_imports,
    _is_one_to_one,
    _relationship_field_context,
    _enum_field_context,
    build_repository_context,
)
from apps.spring_generator.emit.javatypes import java_type_for
from apps.spring_generator.emit.naming import pascal_case


@dataclass(frozen=True)
class InheritanceEntityContext:
    package: str
    class_name: str
    table_name: str | None
    extends_class_name: str | None
    discriminator_column: str | None
    discriminator_value: str
    fields: tuple[FieldContext, ...]
    import_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class InheritanceHierarchyContext:
    root: InheritanceEntityContext
    subclasses: tuple[InheritanceEntityContext, ...]
    repository: RepositoryContext


def _field_imports(field: FieldContext, *, column) -> set[str]:
    imports: set[str] = set()
    if column.enum_type_name is None and not any(
        annotation in ("@ManyToOne", "@OneToOne") for annotation in field.annotations
    ):
        java_type = java_type_for(column.type)
        if java_type.import_fqn is not None:
            imports.add(java_type.import_fqn)

    for annotation in field.annotations:
        if annotation == "@ManyToOne":
            imports.add("jakarta.persistence.ManyToOne")
        if annotation == "@OneToOne":
            imports.add("jakarta.persistence.OneToOne")
        if annotation.startswith("@JoinColumn"):
            imports.add("jakarta.persistence.JoinColumn")
        if annotation.startswith("@Enumerated"):
            imports.add("jakarta.persistence.Enumerated")
            imports.add("jakarta.persistence.EnumType")
        if annotation == "@NotNull":
            imports.add("jakarta.validation.constraints.NotNull")
        if annotation.startswith("@Size"):
            imports.add("jakarta.validation.constraints.Size")
    return imports


def _column_field_context(column, *, table: Table, foreign_key: ForeignKey | None, is_primary_key: bool) -> FieldContext:
    if foreign_key is not None:
        return _relationship_field_context(column, foreign_key=foreign_key, table=table)
    if column.enum_type_name is not None:
        return _enum_field_context(column)
    return _field_context(column, is_primary_key=is_primary_key)


def _build_fields_for_owner(
    table: Table,
    *,
    owner_class_id: str,
    include_structural_root_fields: bool,
) -> tuple[tuple[FieldContext, ...], set[str]]:
    pk_column_name = table.primary_key.column_names[0]
    fk_by_column_name: dict[str, ForeignKey] = {}
    for foreign_key in table.foreign_keys:
        for column_name in foreign_key.column_names:
            fk_by_column_name[column_name] = foreign_key

    fields: list[FieldContext] = []
    imports: set[str] = set()
    for column in table.columns:
        if column.name == table.discriminator_column:
            continue

        is_primary_key = column.name == pk_column_name
        foreign_key = None if is_primary_key else fk_by_column_name.get(column.name)
        belongs_to_root_fk = foreign_key is not None and column.owning_class_id is None and include_structural_root_fields
        belongs_to_owner = column.owning_class_id == owner_class_id
        belongs_to_root_pk = is_primary_key and include_structural_root_fields

        if not belongs_to_root_pk and not belongs_to_root_fk and not belongs_to_owner:
            continue

        field = _column_field_context(
            column,
            table=table,
            foreign_key=foreign_key,
            is_primary_key=is_primary_key,
        )
        fields.append(field)
        imports.update(_field_imports(field, column=column))

    return tuple(fields), imports


def _entity_imports(
    *,
    base_package: str,
    field_imports: set[str],
    is_root: bool,
    has_fields: bool,
) -> tuple[tuple[str, ...], ...]:
    imports = set(field_imports)
    imports.add("jakarta.persistence.Entity")
    imports.add("jakarta.persistence.DiscriminatorValue")
    if has_fields:
        imports.add("jakarta.persistence.Column")
    if is_root:
        imports.add("jakarta.persistence.Table")
        imports.add("jakarta.persistence.Id")
        imports.add("jakarta.persistence.GeneratedValue")
        imports.add("jakarta.persistence.GenerationType")
        imports.add("jakarta.persistence.Inheritance")
        imports.add("jakarta.persistence.InheritanceType")
        imports.add("jakarta.persistence.DiscriminatorColumn")
    return _group_imports(base_package, imports)


def build_inheritance_hierarchy_context(table: Table, *, base_package: str) -> InheritanceHierarchyContext:
    root_class_id = table.source_class_ids[0]
    root_class_name = pascal_case(table.name)
    root_fields, root_field_imports = _build_fields_for_owner(
        table,
        owner_class_id=root_class_id,
        include_structural_root_fields=True,
    )
    root = InheritanceEntityContext(
        package="{}.domain".format(base_package),
        class_name=root_class_name,
        table_name=table.name,
        extends_class_name=None,
        discriminator_column=table.discriminator_column,
        discriminator_value=table.discriminator_values[root_class_id],
        fields=root_fields,
        import_groups=_entity_imports(
            base_package=base_package,
            field_imports=root_field_imports,
            is_root=True,
            has_fields=bool(root_fields),
        ),
    )

    subclasses: list[InheritanceEntityContext] = []
    for class_id in table.source_class_ids[1:]:
        fields, field_imports = _build_fields_for_owner(
            table,
            owner_class_id=class_id,
            include_structural_root_fields=False,
        )
        subclasses.append(
            InheritanceEntityContext(
                package="{}.domain".format(base_package),
                class_name=pascal_case(table.discriminator_values[class_id]),
                table_name=None,
                extends_class_name=root_class_name,
                discriminator_column=None,
                discriminator_value=table.discriminator_values[class_id],
                fields=fields,
                import_groups=_entity_imports(
                    base_package=base_package,
                    field_imports=field_imports,
                    is_root=False,
                    has_fields=bool(fields),
                ),
            )
        )

    return InheritanceHierarchyContext(
        root=root,
        subclasses=tuple(subclasses),
        repository=build_repository_context(table, base_package=base_package),
    )
