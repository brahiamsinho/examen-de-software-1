"""Strict, pure, model-free parser of the reserved `"profile"` key of one
`generation_metadata` entry (design.md DD135-DD140).

Strictness applies only inside `"profile"`: keys outside it are never
read. Within one entry the validation rules are applied in numeric order
(1..12) and the first failing rule raises `InvalidGenerationProfileError`.
Zero declared keys canonicalize to `None` (DD133).
"""
from collections.abc import Mapping

from apps.relational_mapping.domain.profile import (
    _CRUD_ORDER,
    ColumnProfile,
    CrudOperation,
    DefaultSort,
    SortDirection,
    TableProfile,
)
from apps.relational_mapping.mapping.errors import InvalidGenerationProfileError
from apps.uml_modeling.domain.ids import ElementId

_TABLE_KEYS = ("entity", "auditable", "readOnly", "crud", "defaultSort")
_COLUMN_KEYS = ("searchable", "sortable", "readOnly")
_TABLE_BOOLEAN_KEYS = ("entity", "auditable", "readOnly")
_DEFAULT_SORT_KEYS = ("attribute", "direction")


def _profile_body(
    element_id: ElementId, entry: object, allowed: tuple[str, ...], level: str
) -> Mapping[str, object] | None:
    """Rules 1-3: the validated `"profile"` mapping, or `None` when nothing is declared."""
    if not isinstance(entry, Mapping):
        raise InvalidGenerationProfileError(element_id, "metadata entry is not a mapping")
    if "profile" not in entry:
        return None
    body = entry["profile"]
    if not isinstance(body, Mapping):
        raise InvalidGenerationProfileError(element_id, "expected an object", key="profile")
    for key in body:
        if key not in allowed:
            raise InvalidGenerationProfileError(
                element_id, f"unknown {level}-level profile key", key=key
            )
    return body or None


def _boolean(element_id: ElementId, body: Mapping[str, object], key: str) -> bool | None:
    """Rule 4: strict `isinstance(value, bool)`; absent means undeclared."""
    if key not in body:
        return None
    value = body[key]
    if not isinstance(value, bool):
        raise InvalidGenerationProfileError(element_id, "expected a boolean", key=key)
    return value


def _crud(element_id: ElementId, body: Mapping[str, object]) -> tuple[CrudOperation, ...] | None:
    """Rules 5-7, then canonical `create, read, update, delete` order (DD134)."""
    if "crud" not in body:
        return None
    raw = body["crud"]
    if not isinstance(raw, (list, tuple)) or not all(isinstance(item, str) for item in raw):
        raise InvalidGenerationProfileError(
            element_id, "expected a list of CRUD operations", key="crud"
        )
    valid = {operation.value for operation in CrudOperation}
    for item in raw:
        if item not in valid:
            raise InvalidGenerationProfileError(
                element_id, f"unknown CRUD operation {item!r}", key="crud"
            )
    seen: set[str] = set()
    for item in raw:
        if item in seen:
            raise InvalidGenerationProfileError(
                element_id, f"duplicate CRUD operation {item!r}", key="crud"
            )
        seen.add(item)
    return tuple(operation for operation in _CRUD_ORDER if operation.value in seen)


def _default_sort(element_id: ElementId, body: Mapping[str, object]) -> DefaultSort | None:
    """Rules 8-12; the attribute id is stored unresolved (DD140)."""
    if "defaultSort" not in body:
        return None
    raw = body["defaultSort"]
    if not isinstance(raw, Mapping):
        raise InvalidGenerationProfileError(
            element_id,
            "expected an object with 'attribute' and 'direction'",
            key="defaultSort",
        )
    for name in _DEFAULT_SORT_KEYS:
        if name not in raw:
            raise InvalidGenerationProfileError(
                element_id, f"missing required key {name!r}", key="defaultSort"
            )
    for name in raw:
        if name not in _DEFAULT_SORT_KEYS:
            raise InvalidGenerationProfileError(
                element_id, "unknown key", key=f"defaultSort.{name}"
            )
    attribute = raw["attribute"]
    if not isinstance(attribute, str) or not attribute:
        raise InvalidGenerationProfileError(
            element_id, "expected a non-empty string", key="defaultSort.attribute"
        )
    direction = raw["direction"]
    if not isinstance(direction, str) or direction not in {m.value for m in SortDirection}:
        raise InvalidGenerationProfileError(
            element_id, "expected 'asc' or 'desc'", key="defaultSort.direction"
        )
    return DefaultSort(ElementId(attribute), SortDirection(direction))


def parse_table_profile(element_id: ElementId, entry: object) -> TableProfile | None:
    """Class-level entry -> `TableProfile`, or `None` when nothing is declared."""
    body = _profile_body(element_id, entry, _TABLE_KEYS, "table")
    if body is None:
        return None
    entity, auditable, read_only = (
        _boolean(element_id, body, key) for key in _TABLE_BOOLEAN_KEYS
    )
    return TableProfile(
        entity=entity,
        auditable=auditable,
        read_only=read_only,
        crud=_crud(element_id, body),
        default_sort=_default_sort(element_id, body),
    )


def parse_column_profile(element_id: ElementId, entry: object) -> ColumnProfile | None:
    """Attribute-level entry -> `ColumnProfile`, or `None` when nothing is declared."""
    body = _profile_body(element_id, entry, _COLUMN_KEYS, "column")
    if body is None:
        return None
    searchable, sortable, read_only = (_boolean(element_id, body, key) for key in _COLUMN_KEYS)
    return ColumnProfile(searchable=searchable, sortable=sortable, read_only=read_only)
