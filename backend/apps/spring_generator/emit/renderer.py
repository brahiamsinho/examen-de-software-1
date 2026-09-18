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

from apps.relational_mapping.domain.schema import Table
from apps.spring_generator.domain.sources import GeneratedFile, GeneratedSources
from apps.spring_generator.emit.context import build_entity_context, build_repository_context
from apps.spring_generator.emit.errors import reject_out_of_scope
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


def generate_table_sources(table: Table, *, base_package: str = "com.modelia.generated") -> GeneratedSources:
    _validate_base_package(base_package)
    reject_out_of_scope(table)

    entity_context = build_entity_context(table, base_package=base_package)
    repository_context = build_repository_context(table, base_package=base_package)

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

    pkg_path = package_path(base_package)
    entity_path = "src/main/java/{}/domain/{}.java".format(pkg_path, entity_context.class_name)
    repository_path = "src/main/java/{}/persistence/{}.java".format(pkg_path, repository_context.repository_name)

    return GeneratedSources(
        files=(
            GeneratedFile(path=entity_path, contents=entity_source),
            GeneratedFile(path=repository_path, contents=repository_source),
        )
    )
