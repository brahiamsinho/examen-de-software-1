"""Builds frozen `EntityContext`/`RepositoryContext` template contexts
(design.md DD9-DD12). All branching over `ColumnType`, annotation
choice, and import selection lives here so `emit/templates/*.java.j2`
stay purely data-driven (DD2, DD13).

Per the DD14 guard, string assembly in this module uses only `.format()`
and reassignment loops — never `+`/`str.join`/`%`/f-string concatenation
of the generator's own Python source.
"""
from dataclasses import dataclass

from apps.relational_mapping.domain.schema import EnumType, ForeignKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.javatypes import java_type_for
from apps.spring_generator.emit.naming import (
    camel_case,
    pascal_case,
    relationship_base_name,
    resource_path_segment,
    screaming_snake_case,
)

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


@dataclass(frozen=True)
class DtoFieldContext:
    name: str                          # camelCase Java identifier; a FK column keeps its "Id" suffix (DD38)
    java_type: str                     # "UUID" for a FK column, never the related entity type
    getter: str
    setter: str
    annotations: tuple[str, ...]       # request-only: @NotNull, @Size; () on every response field


@dataclass(frozen=True)
class DtoContext:
    package: str
    class_name: str
    fields: tuple[DtoFieldContext, ...]
    import_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class EnumConstantContext:
    name: str        # SCREAMING_SNAKE Java constant (DD31)
    label: str       # verbatim EnumType label, preserved (DD32)


@dataclass(frozen=True)
class EnumContext:
    package: str
    class_name: str
    constants: tuple[EnumConstantContext, ...]


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


def _join_column_annotation(column, *, unique: bool) -> str:
    """DD25: `@JoinColumn` replaces `@Column` on a relationship field,
    fixed attribute order `name, nullable, unique`.
    `referencedColumnName` is never emitted.
    """
    nullable_literal = "true" if column.nullable else "false"
    parts = ['name = "{}"'.format(column.name), "nullable = {}".format(nullable_literal)]
    if unique:
        parts.append("unique = true")
    return "@JoinColumn({})".format(_comma_join(parts))


def _is_one_to_one(foreign_key: ForeignKey, table: Table) -> bool:
    """DD24: `@OneToOne` iff the FK's column set exactly matches one of
    the table's own `unique_constraints` (set comparison, column order
    irrelevant).
    """
    fk_columns = frozenset(foreign_key.column_names)
    return any(fk_columns == frozenset(uc.column_names) for uc in table.unique_constraints)


def _relationship_field_context(column, *, foreign_key: ForeignKey, table: Table) -> FieldContext:
    base_name = relationship_base_name(column.name)
    field_name = camel_case(base_name)
    pascal_name = pascal_case(base_name)
    java_type_name = pascal_case(foreign_key.referenced_table)
    one_to_one = _is_one_to_one(foreign_key, table)

    annotations: list[str] = ["@OneToOne" if one_to_one else "@ManyToOne"]
    annotations.append(_join_column_annotation(column, unique=one_to_one))
    if not column.nullable:
        annotations.append("@NotNull")

    return FieldContext(
        name=field_name,
        java_type=java_type_name,
        getter="get{}".format(pascal_name),
        setter="set{}".format(pascal_name),
        annotations=tuple(annotations),
    )


def _enum_field_context(column) -> FieldContext:
    """DD28/DD29: keys on `column.enum_type_name`, never calls
    `java_type_for`. Annotation order `@Enumerated`, `@Column`,
    `@NotNull` — never `@Size`.
    """
    field_name = camel_case(column.name)
    pascal_name = pascal_case(column.name)
    java_type_name = pascal_case(column.enum_type_name)

    annotations: list[str] = ["@Enumerated(EnumType.STRING)", _column_annotation(column, is_primary_key=False)]
    if not column.nullable:
        annotations.append("@NotNull")

    return FieldContext(
        name=field_name,
        java_type=java_type_name,
        getter="get{}".format(pascal_name),
        setter="set{}".format(pascal_name),
        annotations=tuple(annotations),
    )


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


def _dto_field_context(column, *, for_request: bool) -> DtoFieldContext:
    """DD38: a DTO field never distinguishes a FK column from a scalar
    one — both simply forward `column.type` (a FK column's `ColumnType`
    is already `UUID`, so no relationship-aware branch is needed here,
    unlike `_relationship_field_context`). An enum column still keys on
    `column.enum_type_name`. Request fields carry `@NotNull`/`@Size`;
    response fields carry no annotation at all.
    """
    field_name = camel_case(column.name)
    pascal_name = pascal_case(column.name)
    if column.enum_type_name is not None:
        java_type_name = pascal_case(column.enum_type_name)
    else:
        java_type_name = java_type_for(column.type).name

    annotations: list[str] = []
    if for_request:
        if not column.nullable:
            annotations.append("@NotNull")
        if column.type is ColumnType.VARCHAR and column.length is not None:
            annotations.append("@Size(max = {})".format(column.length))

    return DtoFieldContext(
        name=field_name,
        java_type=java_type_name,
        getter="get{}".format(pascal_name),
        setter="set{}".format(pascal_name),
        annotations=tuple(annotations),
    )


def _build_dto_context(
    table: Table, *, base_package: str, class_name: str, for_request: bool
) -> DtoContext:
    pk_column_name = table.primary_key.column_names[0]

    field_contexts: list[DtoFieldContext] = []
    type_imports: set[str] = set()
    uses_not_null = False
    uses_size = False

    for column in table.columns:
        if for_request and column.name == pk_column_name:
            continue

        field_context = _dto_field_context(column, for_request=for_request)
        field_contexts.append(field_context)

        if column.enum_type_name is not None:
            type_imports.add("{}.domain.{}".format(base_package, field_context.java_type))
        else:
            java_type = java_type_for(column.type)
            if java_type.import_fqn is not None:
                type_imports.add(java_type.import_fqn)

        if "@NotNull" in field_context.annotations:
            uses_not_null = True
        if any(annotation.startswith("@Size") for annotation in field_context.annotations):
            uses_size = True

    all_imports = set(type_imports)
    if uses_not_null:
        all_imports.add("jakarta.validation.constraints.NotNull")
    if uses_size:
        all_imports.add("jakarta.validation.constraints.Size")

    return DtoContext(
        package="{}.application.dto".format(base_package),
        class_name=class_name,
        fields=tuple(field_contexts),
        import_groups=_group_imports(base_package, all_imports),
    )


def build_request_dto_context(table: Table, *, base_package: str) -> DtoContext:
    """DD37/DD38: `<E>RequestDto` omits the primary key column."""
    class_name = "{}RequestDto".format(pascal_case(table.name))
    return _build_dto_context(table, base_package=base_package, class_name=class_name, for_request=True)


def build_response_dto_context(table: Table, *, base_package: str) -> DtoContext:
    """DD37/DD38: `<E>ResponseDto` includes every column, PK included,
    with no validation annotation on any field.
    """
    class_name = "{}ResponseDto".format(pascal_case(table.name))
    return _build_dto_context(table, base_package=base_package, class_name=class_name, for_request=False)


def build_entity_context(table: Table, *, base_package: str) -> EntityContext:
    pk_column_name = table.primary_key.column_names[0]
    fk_by_column_name: dict[str, ForeignKey] = {}
    for foreign_key in table.foreign_keys:
        for column_name in foreign_key.column_names:
            fk_by_column_name[column_name] = foreign_key

    field_contexts: list[FieldContext] = []
    type_imports: set[str] = set()
    uses_not_null = False
    uses_size = False
    uses_many_to_one = False
    uses_one_to_one = False
    uses_join_column = False
    uses_enumerated = False

    for column in table.columns:
        is_primary_key = column.name == pk_column_name
        foreign_key = None if is_primary_key else fk_by_column_name.get(column.name)
        is_enum = not is_primary_key and foreign_key is None and column.enum_type_name is not None

        if is_primary_key:
            field_contexts.append(_field_context(column, is_primary_key=True))
            java_type = java_type_for(column.type)
            if java_type.import_fqn is not None:
                type_imports.add(java_type.import_fqn)
        elif foreign_key is not None:
            # DD23/DD28: FK columns bypass javatypes.py's scalar lookup
            # entirely — the second java_type_for call site must skip
            # them the same way _field_context does.
            field_contexts.append(_relationship_field_context(column, foreign_key=foreign_key, table=table))
            uses_join_column = True
            if _is_one_to_one(foreign_key, table):
                uses_one_to_one = True
            else:
                uses_many_to_one = True
            if not column.nullable:
                uses_not_null = True
        elif is_enum:
            # DD28: enum columns bypass javatypes.py's scalar lookup
            # entirely (no `ColumnType.ENUM` row exists) — this second
            # call site must skip them the same way _field_context does.
            field_contexts.append(_enum_field_context(column))
            uses_enumerated = True
            if not column.nullable:
                uses_not_null = True
        else:
            field_contexts.append(_field_context(column, is_primary_key=False))
            java_type = java_type_for(column.type)
            if java_type.import_fqn is not None:
                type_imports.add(java_type.import_fqn)
            if not column.nullable:
                uses_not_null = True
            if column.type is ColumnType.VARCHAR and column.length is not None:
                uses_size = True

    all_imports = set(_ENTITY_FIXED_IMPORTS) | type_imports
    if uses_not_null:
        all_imports.add("jakarta.validation.constraints.NotNull")
    if uses_size:
        all_imports.add("jakarta.validation.constraints.Size")
    if uses_many_to_one:
        all_imports.add("jakarta.persistence.ManyToOne")
    if uses_one_to_one:
        all_imports.add("jakarta.persistence.OneToOne")
    if uses_join_column:
        all_imports.add("jakarta.persistence.JoinColumn")
    if uses_enumerated:
        all_imports.add("jakarta.persistence.Enumerated")
        all_imports.add("jakarta.persistence.EnumType")

    return EntityContext(
        package="{}.domain".format(base_package),
        class_name=pascal_case(table.name),
        table_name=table.name,
        fields=tuple(field_contexts),
        import_groups=_group_imports(base_package, all_imports),
    )


def build_enum_context(enum_type: EnumType, *, base_package: str) -> EnumContext:
    constants = tuple(
        EnumConstantContext(name=screaming_snake_case(label), label=label) for label in enum_type.labels
    )
    return EnumContext(
        package="{}.domain".format(base_package),
        class_name=pascal_case(enum_type.name),
        constants=constants,
    )


@dataclass(frozen=True)
class RepositoryDependencyContext:
    field_name: str                 # "categoryRepository"
    type_name: str                  # "CategoryRepository"
    entity_type: str                # "Category"


@dataclass(frozen=True)
class ServiceContext:
    package: str
    class_name: str
    entity_class: str
    repository_field: str           # own repository, always first (DD50c)
    repository_type: str
    dependencies: tuple[RepositoryDependencyContext, ...]   # deduped (DD40)
    constructor_parameters: str     # precomputed via _comma_join (DD49)
    constructor_assignments: tuple[str, ...]
    to_response_statements: tuple[str, ...]                 # DD44
    apply_request_statements: tuple[str, ...]               # DD44
    resource_name: str              # table.name, for ResourceNotFoundException
    import_groups: tuple[tuple[str, ...], ...]


def _repository_field_for(referenced_table: str) -> str:
    return "{}Repository".format(camel_case(referenced_table))


def _repository_type_for(referenced_table: str) -> str:
    return "{}Repository".format(pascal_case(referenced_table))


def _to_response_statement_for_pk() -> str:
    return "dto.setId(entity.getId());"


def _to_response_statement_for_field(column) -> str:
    """Scalar and enum fields share this shape: the DTO field and the
    entity field use the same pascal-cased column name (DD38's naming
    only diverges from the entity for FK columns).
    """
    pascal_name = pascal_case(column.name)
    return "dto.set{0}(entity.get{0}());".format(pascal_name)


def _apply_request_statement_for_field(column) -> str:
    pascal_name = pascal_case(column.name)
    return "entity.set{0}(request.get{0}());".format(pascal_name)


def _to_response_statement_for_fk(column) -> str:
    """DD44: `entity.getCategory() == null ? null : entity.getCategory().getId()`
    is safe regardless of nullability because the DD-established fetch
    is EAGER, so this ternary form is used uniformly for every FK field.
    """
    dto_pascal = pascal_case(column.name)
    entity_pascal = pascal_case(relationship_base_name(column.name))
    return (
        "dto.set{dto_pascal}(entity.get{entity_pascal}() == null "
        "? null : entity.get{entity_pascal}().getId());"
    ).format(dto_pascal=dto_pascal, entity_pascal=entity_pascal)


def _apply_request_statement_for_fk(column, foreign_key: ForeignKey, *, repository_field: str) -> str:
    """DD40: FK resolution always goes through `repository.findById(...)
    .orElseThrow(...)`, never `getReference`. A nullable FK whose DTO
    value is `null` skips the lookup and sets `null` instead.
    """
    dto_pascal = pascal_case(column.name)
    entity_pascal = pascal_case(relationship_base_name(column.name))
    dto_getter = "request.get{}()".format(dto_pascal)
    resource_name = foreign_key.referenced_table

    if column.nullable:
        return (
            "if ({dto_getter} == null) {{\n"
            "            entity.set{entity_pascal}(null);\n"
            "        }} else {{\n"
            "            entity.set{entity_pascal}({repository_field}.findById({dto_getter})\n"
            "                    .orElseThrow(() -> new ResourceNotFoundException(\"{resource_name}\", "
            "{dto_getter})));\n"
            "        }}"
        ).format(
            dto_getter=dto_getter,
            entity_pascal=entity_pascal,
            repository_field=repository_field,
            resource_name=resource_name,
        )
    return (
        "entity.set{entity_pascal}({repository_field}.findById({dto_getter})"
        ".orElseThrow(() -> new ResourceNotFoundException(\"{resource_name}\", {dto_getter})));"
    ).format(
        entity_pascal=entity_pascal,
        repository_field=repository_field,
        dto_getter=dto_getter,
        resource_name=resource_name,
    )


def build_service_context(table: Table, *, base_package: str) -> ServiceContext:
    entity_class = pascal_case(table.name)
    own_repository_field = _repository_field_for(table.name)
    own_repository_type = _repository_type_for(table.name)

    pk_column_name = table.primary_key.column_names[0]
    fk_by_column_name: dict[str, ForeignKey] = {}
    for foreign_key in table.foreign_keys:
        for column_name in foreign_key.column_names:
            fk_by_column_name[column_name] = foreign_key

    dependencies: list[RepositoryDependencyContext] = []
    seen_referenced_tables: set[str] = {table.name}
    for foreign_key in table.foreign_keys:
        referenced_table = foreign_key.referenced_table
        if referenced_table in seen_referenced_tables:
            continue
        seen_referenced_tables.add(referenced_table)
        dependencies.append(
            RepositoryDependencyContext(
                field_name=_repository_field_for(referenced_table),
                type_name=_repository_type_for(referenced_table),
                entity_type=pascal_case(referenced_table),
            )
        )

    to_response_statements: list[str] = []
    apply_request_statements: list[str] = []

    for column in table.columns:
        is_primary_key = column.name == pk_column_name
        foreign_key = None if is_primary_key else fk_by_column_name.get(column.name)

        if is_primary_key:
            to_response_statements.append(_to_response_statement_for_pk())
            continue

        if foreign_key is not None:
            repository_field = (
                own_repository_field
                if foreign_key.referenced_table == table.name
                else _repository_field_for(foreign_key.referenced_table)
            )
            to_response_statements.append(_to_response_statement_for_fk(column))
            apply_request_statements.append(
                _apply_request_statement_for_fk(column, foreign_key, repository_field=repository_field)
            )
        else:
            to_response_statements.append(_to_response_statement_for_field(column))
            apply_request_statements.append(_apply_request_statement_for_field(column))

    own_parameter = "{} {}".format(own_repository_type, own_repository_field)
    dependency_parameters = ["{} {}".format(dep.type_name, dep.field_name) for dep in dependencies]
    constructor_parameters = _comma_join([own_parameter] + dependency_parameters)

    own_assignment = "this.{0} = {0};".format(own_repository_field)
    dependency_assignments = ["this.{0} = {0};".format(dep.field_name) for dep in dependencies]
    constructor_assignments = tuple([own_assignment] + dependency_assignments)

    imports = {
        "org.springframework.stereotype.Service",
        "org.springframework.transaction.annotation.Transactional",
        "org.springframework.data.domain.Page",
        "org.springframework.data.domain.Pageable",
        "java.util.UUID",
        "{}.domain.{}".format(base_package, entity_class),
        "{}.persistence.{}".format(base_package, own_repository_type),
        "{}.application.dto.{}RequestDto".format(base_package, entity_class),
        "{}.application.dto.{}ResponseDto".format(base_package, entity_class),
        "{}.errors.ResourceNotFoundException".format(base_package),
    }
    for dependency in dependencies:
        imports.add("{}.persistence.{}".format(base_package, dependency.type_name))

    return ServiceContext(
        package="{}.application".format(base_package),
        class_name="{}Service".format(entity_class),
        entity_class=entity_class,
        repository_field=own_repository_field,
        repository_type=own_repository_type,
        dependencies=tuple(dependencies),
        constructor_parameters=constructor_parameters,
        constructor_assignments=constructor_assignments,
        to_response_statements=tuple(to_response_statements),
        apply_request_statements=tuple(apply_request_statements),
        resource_name=table.name,
        import_groups=_group_imports(base_package, imports),
    )


@dataclass(frozen=True)
class ControllerContext:
    package: str                    # "{base_package}.api"
    class_name: str                 # "<E>Controller"
    service_field: str
    service_type: str
    request_dto: str
    response_dto: str
    resource_path: str              # "/api/order-lines"                  (DD45)
    import_groups: tuple[tuple[str, ...], ...]


def build_controller_context(table: Table, *, base_package: str) -> ControllerContext:
    entity_class = pascal_case(table.name)
    service_field = "{}Service".format(camel_case(table.name))
    service_type = "{}Service".format(entity_class)
    request_dto = "{}RequestDto".format(entity_class)
    response_dto = "{}ResponseDto".format(entity_class)
    resource_path = "/api/{}".format(resource_path_segment(table.name))

    imports = {
        "org.springframework.web.bind.annotation.RestController",
        "org.springframework.web.bind.annotation.RequestMapping",
        "org.springframework.web.bind.annotation.PostMapping",
        "org.springframework.web.bind.annotation.GetMapping",
        "org.springframework.web.bind.annotation.PutMapping",
        "org.springframework.web.bind.annotation.DeleteMapping",
        "org.springframework.web.bind.annotation.PathVariable",
        "org.springframework.web.bind.annotation.RequestBody",
        "org.springframework.web.bind.annotation.ResponseStatus",
        "org.springframework.http.HttpStatus",
        "org.springframework.data.domain.Page",
        "org.springframework.data.domain.Pageable",
        "jakarta.validation.Valid",
        "java.util.UUID",
        "{}.application.{}".format(base_package, service_type),
        "{}.application.dto.{}".format(base_package, request_dto),
        "{}.application.dto.{}".format(base_package, response_dto),
    }

    return ControllerContext(
        package="{}.api".format(base_package),
        class_name="{}Controller".format(entity_class),
        service_field=service_field,
        service_type=service_type,
        request_dto=request_dto,
        response_dto=response_dto,
        resource_path=resource_path,
        import_groups=_group_imports(base_package, imports),
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
