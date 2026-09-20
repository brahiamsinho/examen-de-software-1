"""Generation profile -> declared-keys dict (design.md DD142, DD145, DD146).

Profile objects are read duck-typed with `getattr(..., None)`, so this module
needs no import from `apps.relational_mapping` (DD123). A key the author did not
declare is omitted, never `null` (DD145); `entity` and `aliases` are never read
(DD138, DD139).
"""

# (JSON key, profile attribute) in section 33 declaration order.
_COLUMN_KEYS = (("searchable", "searchable"), ("sortable", "sortable"), ("readOnly", "read_only"))
_TABLE_FLAGS = (("auditable", "auditable"), ("readOnly", "read_only"))


def _text(value):
    """A StrEnum member's wire value, duck-typed: no `apps.relational_mapping` import."""
    return getattr(value, "value", value)


def _declared(profile, keys) -> dict:
    declared = {}
    for json_key, field in keys:
        value = getattr(profile, field, None)
        if value is not None:
            declared[json_key] = value
    return declared


def build_column_profile(profile) -> dict | None:
    if profile is None:
        return None
    return _declared(profile, _COLUMN_KEYS) or None


def build_table_profile(profile, resolve_attribute) -> dict | None:
    if profile is None:
        return None
    declared = _declared(profile, _TABLE_FLAGS)
    crud = getattr(profile, "crud", None)
    if crud is not None:
        declared["crud"] = [_text(operation) for operation in crud]
    default_sort = getattr(profile, "default_sort", None)
    if default_sort is not None:
        declared["defaultSort"] = {
            "attribute": resolve_attribute(default_sort.attribute_id),
            "direction": _text(default_sort.direction),
        }
    return declared or None
