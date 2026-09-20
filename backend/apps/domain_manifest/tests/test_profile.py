"""Profile shaping (spec: Declared-Facts-Only Emission; design DD142, DD145, DD146).

Tests may import `apps.relational_mapping`; only `builder/**` is guarded against it.
"""
from types import SimpleNamespace

import pytest
from apps.domain_manifest.builder.profile import build_column_profile, build_table_profile
from apps.relational_mapping.domain.profile import (
    ColumnProfile,
    CrudOperation,
    DefaultSort,
    SortDirection,
    TableProfile,
)


class _Spy:
    """A `resolve_attribute` stand-in that records its calls."""

    def __init__(self, name="total"):
        self.name, self.calls = name, []

    def __call__(self, attribute_id):
        self.calls.append(attribute_id)
        return self.name


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        (ColumnProfile(searchable=True), {"searchable": True}),
        (ColumnProfile(sortable=True), {"sortable": True}),
        (ColumnProfile(read_only=True), {"readOnly": True}),
        (ColumnProfile(searchable=True, sortable=False, read_only=True), {"searchable": True, "sortable": False, "readOnly": True}),
        (ColumnProfile(searchable=False), {"searchable": False}),
        (SimpleNamespace(sortable=True), {"sortable": True}),
        (ColumnProfile(), None),
        (SimpleNamespace(), None),
        (None, None),
    ],
)
def test_build_column_profile(profile, expected):
    assert build_column_profile(profile) == expected


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        (TableProfile(auditable=True), {"auditable": True}),
        (TableProfile(read_only=False), {"readOnly": False}),
        (TableProfile(auditable=False, read_only=True), {"auditable": False, "readOnly": True}),
        (TableProfile(entity=True), None),
        (TableProfile(entity=True, auditable=True), {"auditable": True}),
        (TableProfile(), None),
        (SimpleNamespace(), None),
        (None, None),
    ],
)
def test_build_table_profile_flags(profile, expected):
    spy = _Spy()

    assert build_table_profile(profile, spy) == expected
    assert spy.calls == []  # no default_sort declared: the resolver is never consulted


def test_crud_is_a_list_of_plain_strings_in_declared_order():
    profile = TableProfile(crud=(CrudOperation.CREATE, CrudOperation.READ))

    crud = build_table_profile(profile, _Spy())["crud"]

    assert crud == ["create", "read"]
    assert type(crud) is list and all(type(item) is str for item in crud)


def test_crud_is_not_re_sorted():
    profile = SimpleNamespace(crud=("delete", "create"))

    assert build_table_profile(profile, _Spy())["crud"] == ["delete", "create"]


@pytest.mark.parametrize(("direction", "text"), [(SortDirection.ASC, "asc"), (SortDirection.DESC, "desc")])
def test_default_sort_shape_and_plain_string_direction(direction, text):
    spy = _Spy("fullName")
    profile = TableProfile(default_sort=DefaultSort(attribute_id="a-1", direction=direction))

    default_sort = build_table_profile(profile, spy)["defaultSort"]

    assert default_sort == {"attribute": "fullName", "direction": text}
    assert type(default_sort["direction"]) is str
    assert spy.calls == ["a-1"]


def test_builder_insertion_order_is_the_section_33_declaration_order():
    profile = TableProfile(
        auditable=True,
        read_only=False,
        crud=(CrudOperation.READ,),
        default_sort=DefaultSort(attribute_id="a-1", direction=SortDirection.ASC),
    )

    assert list(build_table_profile(profile, _Spy())) == ["auditable", "readOnly", "crud", "defaultSort"]
