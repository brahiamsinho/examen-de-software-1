"""RED: apps.spring_generator.emit.context.DtoContext/DtoFieldContext and
build_request_dto_context/build_response_dto_context do not exist yet.

Covers: DD37 (application/dto/ package, two classes) and DD38 (field
rules: PK omitted from request, FK column -> flat UUID field, enum
column keeps its enum type, @NotNull/@Size on request only, zero JPA
annotations). Templates rendered directly via the shared Jinja
`_ENVIRONMENT` (DD49) ahead of `generate_table_sources` wiring, which
Phase 7 adds.
"""
from apps.relational_mapping.domain.schema import Column
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_request_dto_context, build_response_dto_context
from apps.spring_generator.emit.renderer import _ENVIRONMENT
from apps.spring_generator.tests.factories import a_foreign_key, a_table


def _render(context, template_name):
    return _ENVIRONMENT.get_template(template_name).render(
        package=context.package,
        class_name=context.class_name,
        fields=context.fields,
        import_groups=context.import_groups,
    )


def _product_table():
    return a_table(
        name="product",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name="name", type=ColumnType.VARCHAR, nullable=False, length=255),
        ),
    )


def test_dto_context_package_is_application_dto():
    request_context = build_request_dto_context(_product_table(), base_package="com.modelia.generated")
    response_context = build_response_dto_context(_product_table(), base_package="com.modelia.generated")

    assert request_context.package == "com.modelia.generated.application.dto"
    assert response_context.package == "com.modelia.generated.application.dto"


def test_dto_class_names():
    request_context = build_request_dto_context(_product_table(), base_package="com.modelia.generated")
    response_context = build_response_dto_context(_product_table(), base_package="com.modelia.generated")

    assert request_context.class_name == "ProductRequestDto"
    assert response_context.class_name == "ProductResponseDto"


def test_request_dto_omits_primary_key_response_includes_it():
    request_context = build_request_dto_context(_product_table(), base_package="com.modelia.generated")
    response_context = build_response_dto_context(_product_table(), base_package="com.modelia.generated")

    assert "id" not in [field.name for field in request_context.fields]
    assert "id" in [field.name for field in response_context.fields]


def test_request_and_response_source_render_without_jpa_annotations():
    request_source = _render(
        build_request_dto_context(_product_table(), base_package="com.modelia.generated"), "RequestDto.java.j2"
    )
    response_source = _render(
        build_response_dto_context(_product_table(), base_package="com.modelia.generated"), "ResponseDto.java.j2"
    )

    for source in (request_source, response_source):
        assert "jakarta.persistence" not in source
        assert "@Column" not in source
        assert "@JoinColumn" not in source
        assert "@Enumerated" not in source
        assert "@Entity" not in source

    assert "package com.modelia.generated.application.dto;" in request_source
    assert "public class ProductRequestDto {" in request_source
    assert "public class ProductResponseDto {" in response_source


def test_foreign_key_column_becomes_flat_uuid_field_never_entity_type():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        name="order",
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
    )

    request_context = build_request_dto_context(table, base_package="com.modelia.generated")
    response_context = build_response_dto_context(table, base_package="com.modelia.generated")

    request_field = next(field for field in request_context.fields if field.name == "categoryId")
    response_field = next(field for field in response_context.fields if field.name == "categoryId")
    assert request_field.java_type == "UUID"
    assert response_field.java_type == "UUID"

    request_source = _render(request_context, "RequestDto.java.j2")
    response_source = _render(response_context, "ResponseDto.java.j2")
    assert "private UUID categoryId;" in request_source
    assert "private UUID categoryId;" in response_source
    assert "private Category " not in request_source
    assert "private Category " not in response_source


def test_two_foreign_keys_to_the_same_table_stay_distinct():
    billing_fk = a_foreign_key(
        name="fk_order__billing_address_id", column_names=("billing_address_id",), referenced_table="address"
    )
    shipping_fk = a_foreign_key(
        name="fk_order__shipping_address_id", column_names=("shipping_address_id",), referenced_table="address"
    )
    table = a_table(
        name="order",
        columns=(
            Column(name="billing_address_id", type=ColumnType.UUID, nullable=False),
            Column(name="shipping_address_id", type=ColumnType.UUID, nullable=False),
        ),
        foreign_keys=(billing_fk, shipping_fk),
    )

    request_context = build_request_dto_context(table, base_package="com.modelia.generated")
    field_names = {field.name for field in request_context.fields}

    assert "billingAddressId" in field_names
    assert "shippingAddressId" in field_names


def test_enum_column_keeps_enum_type_on_both_dtos():
    table = a_table(
        columns=(Column(name="status", type=ColumnType.ENUM, nullable=False, enum_type_name="order_status"),),
    )

    request_context = build_request_dto_context(table, base_package="com.modelia.generated")
    response_context = build_response_dto_context(table, base_package="com.modelia.generated")

    request_field = next(field for field in request_context.fields if field.name == "status")
    response_field = next(field for field in response_context.fields if field.name == "status")
    assert request_field.java_type == "OrderStatus"
    assert response_field.java_type == "OrderStatus"


def test_not_null_and_size_forwarded_to_request_only():
    table = _product_table()

    request_context = build_request_dto_context(table, base_package="com.modelia.generated")
    response_context = build_response_dto_context(table, base_package="com.modelia.generated")

    request_name_field = next(field for field in request_context.fields if field.name == "name")
    response_name_field = next(field for field in response_context.fields if field.name == "name")
    assert "@NotNull" in request_name_field.annotations
    assert "@Size(max = 255)" in request_name_field.annotations
    assert response_name_field.annotations == ()


def test_field_order_matches_table_columns_declaration_order():
    table = a_table(
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name="name", type=ColumnType.VARCHAR, nullable=False, length=255),
            Column(name="price", type=ColumnType.NUMERIC, nullable=False, precision=10, scale=2),
        ),
    )

    response_context = build_response_dto_context(table, base_package="com.modelia.generated")

    assert [field.name for field in response_context.fields] == ["id", "name", "price"]
