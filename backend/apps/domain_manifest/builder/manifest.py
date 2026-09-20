"""Top level of the manifest: envelope, enums, ordering (design.md DD125, DD131).

Only declared or generated facts are emitted: no searchable/sortable/defaultSort/
auditable/readOnly/aliases and no `generation_metadata` (DD131).
"""
from apps.spring_generator.emit.naming import (
    InvalidJavaIdentifierError,
    InvalidResourcePathError,
    pascal_case,
    screaming_snake_case,
)

from .entities import build_entity

SCHEMA_VERSION = 1


class ManifestError(ValueError):
    """The model holds a name the generator itself would reject."""


def _enum(enum_type) -> dict:
    return {
        "name": pascal_case(enum_type.name),
        # `value` is the Java constant serialized on the wire; `label` is the preserved UML label (DD32).
        "values": [{"value": screaming_snake_case(label), "label": label} for label in enum_type.labels],
    }


def build_manifest(model) -> dict:
    try:
        entities = [build_entity(table) for table in model.tables]
        enums = [_enum(enum_type) for enum_type in model.enum_types]
    except (InvalidJavaIdentifierError, InvalidResourcePathError) as error:
        raise ManifestError(str(error)) from error
    return {
        "schemaVersion": SCHEMA_VERSION,
        "entities": sorted(entities, key=lambda entity: entity["name"]),
        "enums": sorted(enums, key=lambda enum: enum["name"]),
    }
