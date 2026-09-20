import pytest

from apps.relational_mapping.domain.profile import ColumnProfile, SortDirection, TableProfile
from apps.relational_mapping.domain.schema import Column
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import (
    build_repository_context,
    build_service_context,
    build_specification_context,
)
from apps.spring_generator.emit.errors import InvalidDefaultSortError
from apps.spring_generator.tests.factories import (
    a_foreign_key,
    a_table,
    searchable,
    searchable_sortable,
    sortable,
    table_default_sort,
)


def test_searchable_context_uses_java_field_names_and_supported_types():
    table = a_table(
        name="customer",
        columns=(
            Column(name="full_name", type=ColumnType.VARCHAR, source_element_id="name-id", profile=searchable()),
            Column(name="age", type=ColumnType.INTEGER, source_element_id="age-id", profile=searchable()),
            Column(name="notes", type=ColumnType.TEXT, source_element_id="notes-id", profile=searchable()),
            Column(name="total", type=ColumnType.NUMERIC, source_element_id="total-id", profile=searchable()),
            Column(name="rank", type=ColumnType.BIGINT, source_element_id="rank-id", profile=searchable()),
        ),
    )

    context = build_specification_context(table, base_package="com.modelia.generated")

    assert tuple(field.field_name for field in context.filters) == ("fullName", "age", "notes", "total", "rank")
    assert tuple(field.java_type for field in context.filters) == ("String", "Integer", "String", "BigDecimal", "Long")
    assert tuple(field.match_kind for field in context.filters) == (
        "string_contains_ignore_case",
        "numeric_equals",
        "string_contains_ignore_case",
        "numeric_equals",
        "numeric_equals",
    )


def test_profile_context_excludes_pk_fk_enum_unsupported_and_false_values():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        name="product",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False, profile=searchable()),
            Column(name="category_id", type=ColumnType.UUID, profile=searchable()),
            Column(name="status", type=ColumnType.ENUM, enum_type_name="product_status", profile=searchable()),
            Column(name="active", type=ColumnType.BOOLEAN, profile=searchable()),
            Column(name="name", type=ColumnType.VARCHAR, profile=ColumnProfile(searchable=False, sortable=False)),
            Column(name="code", type=ColumnType.VARCHAR, profile=searchable_sortable()),
        ),
        foreign_keys=(fk,),
    )

    specification = build_specification_context(table, base_package="com.modelia.generated")
    service = build_service_context(table, base_package="com.modelia.generated")

    assert tuple(field.field_name for field in specification.filters) == ("code",)
    assert tuple(field.field_name for field in service.sortable_fields) == ("code",)


def test_default_sort_resolves_to_sortable_java_field_and_direction():
    table = a_table(
        name="customer",
        columns=(
            Column(name="full_name", type=ColumnType.VARCHAR, source_element_id="name-id", profile=sortable()),
        ),
        profile=table_default_sort("name-id", SortDirection.DESC),
    )

    context = build_service_context(table, base_package="com.modelia.generated")

    assert context.default_sort.field_name == "fullName"
    assert context.default_sort.direction == "DESC"


@pytest.mark.parametrize(
    ("columns", "profile", "reason"),
    (
        ((Column(name="name", type=ColumnType.VARCHAR, source_element_id="name-id"),), table_default_sort("missing"), "attribute_not_found"),
        ((Column(name="name", type=ColumnType.VARCHAR, source_element_id="name-id"),), table_default_sort("name-id"), "attribute_not_sortable"),
        ((Column(name="id", type=ColumnType.UUID, nullable=False, source_element_id="id-id", profile=sortable()),), table_default_sort("id-id"), "attribute_is_primary_key"),
        ((Column(name="category_id", type=ColumnType.UUID, source_element_id="cat-id", profile=sortable()),), table_default_sort("cat-id"), "attribute_is_foreign_key"),
        ((Column(name="status", type=ColumnType.ENUM, enum_type_name="status", source_element_id="status-id", profile=sortable()),), table_default_sort("status-id"), "attribute_is_enum"),
        ((Column(name="active", type=ColumnType.BOOLEAN, source_element_id="active-id", profile=sortable()),), table_default_sort("active-id"), "attribute_type_unsupported"),
    ),
)
def test_invalid_default_sort_raises_typed_error(columns, profile, reason):
    table = a_table(name="product", columns=columns, foreign_keys=(a_foreign_key(),), profile=profile)

    with pytest.raises(InvalidDefaultSortError) as exc_info:
        build_service_context(table, base_package="com.modelia.generated")

    assert exc_info.value.reason == reason
    assert exc_info.value.table_name == "product"


def test_repository_context_precomputes_jpa_specification_executor_only_for_searchable_tables():
    searchable_table = a_table(name="customer", columns=(Column(name="name", type=ColumnType.VARCHAR, profile=searchable()),))
    plain_table = a_table(name="product")

    searchable_context = build_repository_context(searchable_table, base_package="com.modelia.generated")
    plain_context = build_repository_context(plain_table, base_package="com.modelia.generated")

    assert searchable_context.extends_interfaces == "JpaRepository<Customer, UUID>, JpaSpecificationExecutor<Customer>"
    assert plain_context.extends_interfaces == "JpaRepository<Product, UUID>"
