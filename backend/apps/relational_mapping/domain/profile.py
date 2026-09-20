"""Generation profile value objects (spec section 33; design.md DD132-DD134).

Frozen and hashable by construction: only `bool | None`, `str`, `StrEnum`,
tuples and nested frozen dataclasses. Every field is tri-state: `None`
means "not declared", never an invented default (DD133). Zero framework
imports.
"""
from dataclasses import dataclass
from enum import StrEnum

from apps.uml_modeling.domain.ids import ElementId


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class CrudOperation(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


# Canonical emission order of a declared `crud` subset (DD134).
_CRUD_ORDER = (
    CrudOperation.CREATE,
    CrudOperation.READ,
    CrudOperation.UPDATE,
    CrudOperation.DELETE,
)


@dataclass(frozen=True)
class DefaultSort:
    attribute_id: ElementId
    direction: SortDirection


@dataclass(frozen=True)
class ColumnProfile:
    """JSON keys: searchable, sortable, readOnly."""

    searchable: bool | None = None
    sortable: bool | None = None
    read_only: bool | None = None


@dataclass(frozen=True)
class TableProfile:
    """JSON keys: entity, auditable, readOnly, crud, defaultSort."""

    entity: bool | None = None
    auditable: bool | None = None
    read_only: bool | None = None
    crud: tuple[CrudOperation, ...] | None = None
    default_sort: DefaultSort | None = None


# The controller's own declaration order (Controller.java.j2); mirrored by
# domain_manifest.builder.entities._OPERATIONS, pinned by a cross-app test.
OPERATION_NAMES: tuple[str, ...] = ("create", "findById", "update", "delete", "list", "count")

_CRUD_TO_OPERATIONS = {
    CrudOperation.CREATE: ("create",),
    CrudOperation.READ: ("findById", "list", "count"),
    CrudOperation.UPDATE: ("update",),
    CrudOperation.DELETE: ("delete",),
}
_READ_OPERATIONS = frozenset(_CRUD_TO_OPERATIONS[CrudOperation.READ])


def effective_operations(profile: TableProfile | None) -> tuple[str, ...]:
    """Operation names a table's declared profile leaves enabled (DD160-DD161)."""
    crud = None if profile is None else profile.crud
    allowed = set(OPERATION_NAMES) if crud is None else {name for op in crud for name in _CRUD_TO_OPERATIONS[op]}
    if profile is not None and profile.read_only is True:
        allowed &= _READ_OPERATIONS
    return tuple(name for name in OPERATION_NAMES if name in allowed)
