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
