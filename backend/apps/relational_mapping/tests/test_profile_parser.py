"""Strict parser and error class of the generation profile (generation-profile
spec; DD135-DD140, validation rules 1-12).
"""
import pytest

from apps.relational_mapping.domain.profile import (
    ColumnProfile,
    CrudOperation,
    DefaultSort,
    SortDirection,
    TableProfile,
)
from apps.relational_mapping.mapping.errors import (
    InvalidGenerationProfileError,
    UnmappableModelError,
)
from apps.relational_mapping.mapping.profile_parser import (
    parse_column_profile,
    parse_table_profile,
)
from apps.uml_modeling.domain.ids import ElementId

_ID = ElementId("e1")
_TABLE_UNKNOWN = "unknown table-level profile key"
_COLUMN_UNKNOWN = "unknown column-level profile key"


def test_error_without_key_message_and_attributes():
    exc = InvalidGenerationProfileError(ElementId("e1"), "metadata entry is not a mapping")

    assert str(exc) == "Invalid generation profile for element 'e1': metadata entry is not a mapping"
    assert (exc.element_id, exc.key, exc.reason) == (
        ElementId("e1"),
        None,
        "metadata entry is not a mapping",
    )


def test_error_with_key_message_and_attributes():
    exc = InvalidGenerationProfileError(ElementId("a1"), "expected a boolean", key="searchable")

    assert str(exc) == "Invalid generation profile for element 'a1', key 'searchable': expected a boolean"
    assert (exc.element_id, exc.key, exc.reason) == (ElementId("a1"), "searchable", "expected a boolean")


def test_error_is_an_unmappable_model_error():
    assert issubclass(InvalidGenerationProfileError, UnmappableModelError)
    with pytest.raises(UnmappableModelError):
        raise InvalidGenerationProfileError(ElementId("e1"), "boom")


def test_full_table_entry_parses_with_canonical_crud_and_default_sort():
    entry = {
        "profile": {
            "entity": True,
            "auditable": True,
            "readOnly": False,
            "crud": ["read", "create"],
            "defaultSort": {"attribute": "attr-total", "direction": "desc"},
        }
    }

    assert parse_table_profile(_ID, entry) == TableProfile(
        entity=True,
        auditable=True,
        read_only=False,
        crud=(CrudOperation.CREATE, CrudOperation.READ),
        default_sort=DefaultSort(ElementId("attr-total"), SortDirection.DESC),
    )


def test_full_column_entry_parses():
    entry = {"profile": {"searchable": True, "sortable": True, "readOnly": False}}

    assert parse_column_profile(_ID, entry) == ColumnProfile(
        searchable=True, sortable=True, read_only=False
    )


def test_partial_entries_leave_other_fields_undeclared():
    table = parse_table_profile(_ID, {"profile": {"auditable": True}})
    column = parse_column_profile(_ID, {"profile": {"sortable": True}})

    assert table == TableProfile(auditable=True)
    assert table.entity is None and table.read_only is None and table.crud is None
    assert column == ColumnProfile(sortable=True)
    assert column.searchable is None and column.read_only is None


def test_crud_input_order_does_not_matter():
    shuffled = parse_table_profile(_ID, {"profile": {"crud": ["delete", "read", "create"]}})
    ordered = parse_table_profile(_ID, {"profile": {"crud": ["create", "read", "delete"]}})

    assert shuffled.crud == (CrudOperation.CREATE, CrudOperation.READ, CrudOperation.DELETE)
    assert shuffled == ordered
    assert hash(shuffled) == hash(ordered)


def test_empty_crud_list_is_declared_not_undeclared():
    profile = parse_table_profile(_ID, {"profile": {"crud": []}})

    assert profile is not None
    assert profile.crud == ()


@pytest.mark.parametrize(
    "entry",
    [{"profile": {}}, {}, {"source": "llm", "confidence": 0.9}],
)
@pytest.mark.parametrize("parse", [parse_table_profile, parse_column_profile])
def test_zero_declared_keys_canonicalize_to_none(parse, entry):
    assert parse(_ID, entry) is None


def test_provenance_keys_outside_profile_are_ignored_even_when_malformed():
    entry = {
        "source": "llm",
        "confidence": "not-a-number",
        "aliases": 7,
        "profile": {"auditable": True},
    }

    assert parse_table_profile(_ID, entry) == TableProfile(auditable=True)


def test_entity_false_is_stored():
    assert parse_table_profile(_ID, {"profile": {"entity": False}}).entity is False


def test_unresolvable_default_sort_attribute_is_accepted():
    entry = {"profile": {"defaultSort": {"attribute": "no-such-attribute", "direction": "asc"}}}

    assert parse_table_profile(_ID, entry).default_sort == DefaultSort(
        ElementId("no-such-attribute"), SortDirection.ASC
    )


def test_same_entry_parsed_twice_is_equal_and_hash_equal():
    entry = {
        "profile": {"crud": ["update", "read"], "defaultSort": {"attribute": "a", "direction": "asc"}}
    }

    first, second = parse_table_profile(_ID, entry), parse_table_profile(_ID, entry)

    assert first == second
    assert hash(first) == hash(second)


def _table(**profile):
    return parse_table_profile, {"profile": profile}


def _column(**profile):
    return parse_column_profile, {"profile": profile}


_SORT = {"attribute": "a1", "direction": "asc"}

# (parse function, entry, expected key, expected reason) - single-fault inputs.
_ERROR_CASES = [
    # Rule 1
    (parse_table_profile, ["profile"], None, "metadata entry is not a mapping"),
    (parse_column_profile, "garbage", None, "metadata entry is not a mapping"),
    # Rule 2
    (parse_column_profile, {"profile": ["searchable"]}, "profile", "expected an object"),
    (parse_table_profile, {"profile": "auditable"}, "profile", "expected an object"),
    # Rule 3
    (*_table(colour=True), "colour", _TABLE_UNKNOWN),
    (*_column(colour=True), "colour", _COLUMN_UNKNOWN),
    (*_table(searchable=True), "searchable", _TABLE_UNKNOWN),
    (*_column(crud=["read"]), "crud", _COLUMN_UNKNOWN),
    (*_table(aliases=["x"]), "aliases", _TABLE_UNKNOWN),
    (*_column(required=True), "required", _COLUMN_UNKNOWN),
    (*_column(unique=True), "unique", _COLUMN_UNKNOWN),
    # Rule 4
    *[(*_column(searchable=v), "searchable", "expected a boolean") for v in (1, 0, "true", None)],
    *[(*_table(auditable=v), "auditable", "expected a boolean") for v in (1, 0, "true", None)],
    # Rule 5
    *[
        (*_table(crud=v), "crud", "expected a list of CRUD operations")
        for v in ("read", {"read": True}, ["read", 1])
    ],
    # Rule 6
    (*_table(crud=["read", "READ"]), "crud", "unknown CRUD operation 'READ'"),
    # Rule 7
    (*_table(crud=["read", "create", "read"]), "crud", "duplicate CRUD operation 'read'"),
    # Rule 8
    (
        *_table(defaultSort="attr-total"),
        "defaultSort",
        "expected an object with 'attribute' and 'direction'",
    ),
    # Rule 9
    (*_table(defaultSort={"direction": "asc"}), "defaultSort", "missing required key 'attribute'"),
    (*_table(defaultSort={"attribute": "a1"}), "defaultSort", "missing required key 'direction'"),
    # Rule 10
    (*_table(defaultSort={**_SORT, "nulls": "first"}), "defaultSort.nulls", "unknown key"),
    # Rule 11
    *[
        (*_table(defaultSort={**_SORT, "attribute": v}), "defaultSort.attribute", "expected a non-empty string")
        for v in ("", 5, None)
    ],
    # Rule 12
    *[
        (*_table(defaultSort={**_SORT, "direction": v}), "defaultSort.direction", "expected 'asc' or 'desc'")
        for v in ("ASC", "up", None, ["asc"])
    ],
]


@pytest.mark.parametrize(("parse", "entry", "key", "reason"), _ERROR_CASES)
def test_invalid_entry_raises_with_exact_key_reason_and_message(parse, entry, key, reason):
    with pytest.raises(InvalidGenerationProfileError) as raised:
        parse(_ID, entry)

    exc = raised.value
    assert (exc.element_id, exc.key, exc.reason) == (_ID, key, reason)
    where = "" if key is None else f", key {key!r}"
    assert str(exc) == f"Invalid generation profile for element 'e1'{where}: {reason}"


def test_two_faults_in_one_entry_raise_the_lowest_numbered_rule():
    # "auditable: 1" (rule 4) comes first in dict order, but the unknown key
    # (rule 3) has the lower rule number, so it is the one reported.
    with pytest.raises(InvalidGenerationProfileError) as raised:
        parse_table_profile(_ID, {"profile": {"auditable": 1, "colour": True}})

    assert (raised.value.key, raised.value.reason) == ("colour", _TABLE_UNKNOWN)
