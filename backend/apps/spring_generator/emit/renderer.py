"""Public API (design.md DD3): `generate_table_sources` is a pure
function of its `Table` input to in-memory Java source text. It never
touches the filesystem or a database, and never calls
`relational_mapping`'s `validate()` (spec: Generator Purity).

Pipeline: reject out-of-scope shapes (DD15) -> build contexts (DD9-DD12)
-> render Entity.java.j2 -> render Repository.java.j2. Stage 1 is total
and eager: a rejected `Table` never produces partial output.
"""
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from apps.relational_mapping.domain.schema import EnumType, Table
from apps.spring_generator.domain.sources import GeneratedFile, GeneratedSources
from apps.spring_generator.emit.context import (
    build_controller_context,
    build_entity_context,
    build_enum_context,
    build_repository_context,
    build_request_dto_context,
    build_response_dto_context,
    build_service_context,
)
from apps.spring_generator.emit.inheritance_context import build_inheritance_hierarchy_context
from apps.spring_generator.emit.errors import (
    reject_invalid_resource_path,
    reject_out_of_scope,
    reject_ungeneratable_enum,
)
from apps.spring_generator.emit.naming import package_path

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# DD13: constructed once at module import. StrictUndefined turns a
# missing context key into a loud failure instead of a silently-empty
# Java token; autoescape is HTML-specific and would corrupt Java string
# literals and generics.
_ENVIRONMENT = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    autoescape=False,
)

# DD20: validated base_package keyword parameter.
_BASE_PACKAGE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


def _validate_base_package(base_package: str) -> None:
    if not _BASE_PACKAGE_PATTERN.match(base_package):
        raise ValueError("base_package {!r} is not a valid Java package name".format(base_package))


def _table_has_inheritance_metadata(table: Table) -> bool:
    return table.discriminator_column is not None or bool(table.discriminator_values)


def _render_inheritance_table_sources(table: Table, *, base_package: str) -> GeneratedSources:
    hierarchy_context = build_inheritance_hierarchy_context(table, base_package=base_package)
    template = _ENVIRONMENT.get_template("InheritanceEntity.java.j2")
    pkg_path = package_path(base_package)

    files: list[GeneratedFile] = []
    entity_contexts = [hierarchy_context.root]
    entity_contexts.extend(hierarchy_context.subclasses)
    for entity_context in entity_contexts:
        entity_source = template.render(
            package=entity_context.package,
            class_name=entity_context.class_name,
            table_name=entity_context.table_name,
            extends_class_name=entity_context.extends_class_name,
            discriminator_column=entity_context.discriminator_column,
            discriminator_value=entity_context.discriminator_value,
            fields=entity_context.fields,
            import_groups=entity_context.import_groups,
        )
        entity_path = "src/main/java/{}/domain/{}.java".format(pkg_path, entity_context.class_name)
        files.append(GeneratedFile(path=entity_path, contents=entity_source))

    repository_context = hierarchy_context.repository
    repository_source = _ENVIRONMENT.get_template("Repository.java.j2").render(
        package=repository_context.package,
        class_name=repository_context.class_name,
        repository_name=repository_context.repository_name,
        import_groups=repository_context.import_groups,
    )
    repository_path = "src/main/java/{}/persistence/{}.java".format(pkg_path, repository_context.repository_name)
    files.append(GeneratedFile(path=repository_path, contents=repository_source))

    return GeneratedSources(files=tuple(files))


def generate_table_sources(table: Table, *, base_package: str = "com.modelia.generated") -> GeneratedSources:
    _validate_base_package(base_package)
    reject_out_of_scope(table)
    reject_invalid_resource_path(table)

    if _table_has_inheritance_metadata(table):
        return _render_inheritance_table_sources(table, base_package=base_package)

    entity_context = build_entity_context(table, base_package=base_package)
    repository_context = build_repository_context(table, base_package=base_package)
    request_dto_context = build_request_dto_context(table, base_package=base_package)
    response_dto_context = build_response_dto_context(table, base_package=base_package)
    service_context = build_service_context(table, base_package=base_package)
    controller_context = build_controller_context(table, base_package=base_package)

    entity_source = _ENVIRONMENT.get_template("Entity.java.j2").render(
        package=entity_context.package,
        class_name=entity_context.class_name,
        table_name=entity_context.table_name,
        fields=entity_context.fields,
        import_groups=entity_context.import_groups,
    )
    repository_source = _ENVIRONMENT.get_template("Repository.java.j2").render(
        package=repository_context.package,
        class_name=repository_context.class_name,
        repository_name=repository_context.repository_name,
        import_groups=repository_context.import_groups,
    )
    request_dto_source = _ENVIRONMENT.get_template("RequestDto.java.j2").render(
        package=request_dto_context.package,
        class_name=request_dto_context.class_name,
        fields=request_dto_context.fields,
        import_groups=request_dto_context.import_groups,
    )
    response_dto_source = _ENVIRONMENT.get_template("ResponseDto.java.j2").render(
        package=response_dto_context.package,
        class_name=response_dto_context.class_name,
        fields=response_dto_context.fields,
        import_groups=response_dto_context.import_groups,
    )
    service_source = _ENVIRONMENT.get_template("Service.java.j2").render(
        package=service_context.package,
        class_name=service_context.class_name,
        entity_class=service_context.entity_class,
        repository_field=service_context.repository_field,
        repository_type=service_context.repository_type,
        dependencies=service_context.dependencies,
        constructor_parameters=service_context.constructor_parameters,
        constructor_assignments=service_context.constructor_assignments,
        to_response_statements=service_context.to_response_statements,
        apply_request_statements=service_context.apply_request_statements,
        resource_name=service_context.resource_name,
        import_groups=service_context.import_groups,
    )
    controller_source = _ENVIRONMENT.get_template("Controller.java.j2").render(
        package=controller_context.package,
        class_name=controller_context.class_name,
        service_field=controller_context.service_field,
        service_type=controller_context.service_type,
        request_dto=controller_context.request_dto,
        response_dto=controller_context.response_dto,
        resource_path=controller_context.resource_path,
        import_groups=controller_context.import_groups,
    )

    pkg_path = package_path(base_package)
    entity_path = "src/main/java/{}/domain/{}.java".format(pkg_path, entity_context.class_name)
    repository_path = "src/main/java/{}/persistence/{}.java".format(pkg_path, repository_context.repository_name)
    request_dto_path = "src/main/java/{}/application/dto/{}.java".format(pkg_path, request_dto_context.class_name)
    response_dto_path = "src/main/java/{}/application/dto/{}.java".format(pkg_path, response_dto_context.class_name)
    service_path = "src/main/java/{}/application/{}.java".format(pkg_path, service_context.class_name)
    controller_path = "src/main/java/{}/api/{}.java".format(pkg_path, controller_context.class_name)

    return GeneratedSources(
        files=(
            GeneratedFile(path=entity_path, contents=entity_source),
            GeneratedFile(path=repository_path, contents=repository_source),
            GeneratedFile(path=request_dto_path, contents=request_dto_source),
            GeneratedFile(path=response_dto_path, contents=response_dto_source),
            GeneratedFile(path=service_path, contents=service_source),
            GeneratedFile(path=controller_path, contents=controller_source),
        )
    )


def generate_project_config_sources() -> GeneratedSources:
    """Project-singleton Spring Boot configuration source generator.

    Pure, parameter-free sibling to the table, enum, and shared-error
    generators. It emits exactly one in-memory YAML resource with required
    environment placeholders and performs no package validation because no
    Java package participates in this resource file.
    """
    source = _ENVIRONMENT.get_template("application.yml.j2").render()

    return GeneratedSources(
        files=(
            GeneratedFile(path="src/main/resources/application.yml", contents=source),
        )
    )


def generate_shared_error_sources(*, base_package: str = "com.modelia.generated") -> GeneratedSources:
    """DD42: sibling entry point to `generate_table_sources`, taking no
    `Table`. Reuses the same Jinja `_ENVIRONMENT`, `_validate_base_package`,
    and `package_path`. Pure function of `base_package` alone (DD3) —
    emits the two per-project `errors/` files exactly once per call.
    """
    _validate_base_package(base_package)

    errors_package = "{}.errors".format(base_package)

    exception_source = _ENVIRONMENT.get_template("ResourceNotFoundException.java.j2").render(
        package=errors_package,
    )
    handler_source = _ENVIRONMENT.get_template("GlobalExceptionHandler.java.j2").render(
        package=errors_package,
    )

    pkg_path = package_path(base_package)
    exception_path = "src/main/java/{}/errors/ResourceNotFoundException.java".format(pkg_path)
    handler_path = "src/main/java/{}/errors/GlobalExceptionHandler.java".format(pkg_path)

    return GeneratedSources(
        files=(
            GeneratedFile(path=exception_path, contents=exception_source),
            GeneratedFile(path=handler_path, contents=handler_source),
        )
    )


def generate_enum_source(
    enum_type: EnumType, *, base_package: str = "com.modelia.generated"
) -> GeneratedFile:
    """DD30: sibling entry point to `generate_table_sources`, reusing
    the same Jinja `_ENVIRONMENT`, `_validate_base_package`, and
    `package_path`. Pure function of its `EnumType` input (DD3).
    """
    _validate_base_package(base_package)
    reject_ungeneratable_enum(enum_type)

    enum_context = build_enum_context(enum_type, base_package=base_package)

    enum_source = _ENVIRONMENT.get_template("Enum.java.j2").render(
        package=enum_context.package,
        class_name=enum_context.class_name,
        constants=enum_context.constants,
    )

    pkg_path = package_path(base_package)
    enum_path = "src/main/java/{}/domain/{}.java".format(pkg_path, enum_context.class_name)

    return GeneratedFile(path=enum_path, contents=enum_source)
