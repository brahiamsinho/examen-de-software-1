"""Value-object shape of the generation profile (generation-profile spec,
Requirement: Profile Value Objects; DD132-DD134).
"""
import ast
import dataclasses
import inspect

import pytest

from apps.relational_mapping.domain.profile import (
    ColumnProfile,
    CrudOperation,
    DefaultSort,
    OPERATION_NAMES,
    SortDirection,
    TableProfile,
    effective_operations,
)
from apps.relational_mapping.domain import profile as profile_module
from apps.relational_mapping.mapping import profile_parser
from apps.uml_modeling.domain.ids import ElementId


def test_column_profile_defaults_to_undeclared():
    profile = ColumnProfile()

    assert (profile.searchable, profile.sortable, profile.read_only) == (None, None, None)


def test_table_profile_defaults_to_undeclared():
    profile = TableProfile()

    assert (profile.entity, profile.auditable, profile.read_only) == (None, None, None)
    assert profile.crud is None
    assert profile.default_sort is None


def test_column_profile_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        ColumnProfile(searchable=True).searchable = False


def test_table_profile_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        TableProfile(auditable=True).auditable = False


def _full_table_profile() -> TableProfile:
    return TableProfile(
        auditable=True,
        crud=(CrudOperation.CREATE, CrudOperation.READ),
        default_sort=DefaultSort(ElementId("attr-total"), SortDirection.DESC),
    )


def test_equal_table_profiles_are_equal_and_hash_equal():
    first, second = _full_table_profile(), _full_table_profile()

    assert first == second
    assert hash(first) == hash(second)
    assert {first} == {second}


def test_different_table_profiles_are_not_equal():
    assert _full_table_profile() != TableProfile(auditable=True)


def test_enum_values():
    assert [direction.value for direction in SortDirection] == ["asc", "desc"]
    assert [operation.value for operation in CrudOperation] == ["create", "read", "update", "delete"]


ALL_SIX = ("create", "findById", "update", "delete", "list", "count")
READS = ("findById", "list", "count")
C, R, U, D = CrudOperation.CREATE, CrudOperation.READ, CrudOperation.UPDATE, CrudOperation.DELETE


def test_operation_names_are_the_six_controller_names_in_controller_order():
    assert OPERATION_NAMES == ALL_SIX
    assert type(OPERATION_NAMES) is tuple


# DD161 truth table: (crud, expected when read_only is None/False, expected when read_only is True).
_TRUTH_TABLE = [
    (None, ALL_SIX, READS),
    ((), (), ()),
    ((C,), ("create",), ()),
    ((R,), READS, READS),
    ((U,), ("update",), ()),
    ((D,), ("delete",), ()),
    ((C, R), ("create", "findById", "list", "count"), READS),
    ((C, U, D), ("create", "update", "delete"), ()),
    ((C, R, U, D), ALL_SIX, READS),
]


@pytest.mark.parametrize(("crud", "open_expected", "read_only_expected"), _TRUTH_TABLE)
@pytest.mark.parametrize("read_only", [None, False])
def test_effective_operations_for_a_writable_or_unspecified_profile(crud, open_expected, read_only_expected, read_only):
    assert effective_operations(TableProfile(crud=crud, read_only=read_only)) == open_expected


@pytest.mark.parametrize(("crud", "open_expected", "read_only_expected"), _TRUTH_TABLE)
def test_effective_operations_for_a_read_only_profile(crud, open_expected, read_only_expected):
    assert effective_operations(TableProfile(crud=crud, read_only=True)) == read_only_expected


def test_an_absent_profile_and_an_empty_profile_are_identical():
    assert effective_operations(None) == effective_operations(TableProfile()) == ALL_SIX


def test_the_result_is_a_canonical_deterministic_tuple_of_plain_strings():
    declared = effective_operations(TableProfile(crud=(D, C, R)))

    assert declared == effective_operations(TableProfile(crud=(C, R, D))) == ("create", "findById", "delete", "list", "count")
    assert declared == effective_operations(TableProfile(crud=(D, C, R)))
    assert type(declared) is tuple and all(type(name) is str for name in declared)


_FORBIDDEN_IMPORT_PREFIXES = ("django", "psycopg", "sqlite3", "MySQLdb", "java", "org.springframework")
_PARSER_FORBIDDEN_PREFIXES = (
    "apps.uml_modeling.domain.model",
    "apps.domain_manifest",
    "apps.spring_generator",
)


def _imported_module_names(module) -> list[str]:
    tree = ast.parse(inspect.getsource(module))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_profile_modules_have_zero_framework_imports():
    for module in (profile_module, profile_parser):
        imported = _imported_module_names(module)
        assert imported, f"{module.__name__} imports nothing; the guard would be vacuous"
        for name in imported:
            assert not name.startswith(_FORBIDDEN_IMPORT_PREFIXES), (
                f"{module.__name__} imports forbidden module {name!r}"
            )


def test_profile_parser_is_model_and_consumer_free():
    for name in _imported_module_names(profile_parser):
        assert not name.startswith(_PARSER_FORBIDDEN_PREFIXES), (
            f"profile_parser imports forbidden module {name!r}"
        )
