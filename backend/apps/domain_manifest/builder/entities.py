"""Table -> entity assembly and the fixed CRUD operations (design.md DD125, DD126)."""
from apps.spring_generator.emit.naming import pascal_case, resource_path_segment

from .attributes import attribute_name, build_attributes
from .errors import ManifestError
from .profile import build_table_profile
from .relationships import build_relationships

# The controller's own declaration order (Controller.java.j2): name, method, path suffix, success status.
_OPERATIONS = (
    ("create", "POST", "", 201),
    ("findById", "GET", "/{id}", 200),
    ("update", "PUT", "/{id}", 200),
    ("delete", "DELETE", "/{id}", 204),
    ("list", "GET", "", 200),
    ("count", "GET", "/count", 200),
)


def _has_inheritance(table) -> bool:
    return table.discriminator_column is not None or bool(table.discriminator_values)


def _subtypes(table) -> list[dict]:
    values = [table.discriminator_values[class_id] for class_id in table.source_class_ids[1:]]
    return sorted(({"name": pascal_case(value), "discriminatorValue": value} for value in values), key=lambda subtype: subtype["name"])


def _operations(resource_path: str | None) -> list[dict]:
    if resource_path is None:
        return []
    return [
        {"name": name, "method": method, "path": resource_path + suffix, "successStatus": status}
        for name, method, suffix, status in _OPERATIONS
    ]


def _resolver(table):
    """Map a declared attribute id to the emitted attribute name of this table (DD144).

    The discriminator column is skipped because the attributes builder does not emit it;
    synthetic columns (`source_element_id is None`) never match a declared id.
    """

    def resolve_attribute(attribute_id) -> str:
        for column in table.columns:
            if column.name != table.discriminator_column and column.source_element_id == attribute_id:
                return attribute_name(column)
        raise ManifestError(f"table {table.name!r} declares defaultSort on unknown attribute id {attribute_id!r}")

    return resolve_attribute


def build_entity(table) -> dict:
    # Inheritance tables render as entity + repository only: no controller, so no resource path (DD126).
    resource_path = None if _has_inheritance(table) else "/api/" + resource_path_segment(table.name)
    entity = {
        "name": pascal_case(table.name),
        "table": table.name,
        "resourcePath": resource_path,
        "discriminatorColumn": table.discriminator_column,
        "subtypes": _subtypes(table) if _has_inheritance(table) else [],
        "operations": _operations(resource_path),
        "attributes": build_attributes(table),
        "relationships": build_relationships(table),
        "uniqueConstraints": [
            {"name": unique.name, "columns": list(unique.column_names)}
            for unique in sorted(table.unique_constraints, key=lambda unique: unique.name)
        ],
    }
    profile = build_table_profile(table.profile, _resolver(table))
    if profile is not None:
        entity["profile"] = profile
    return entity
