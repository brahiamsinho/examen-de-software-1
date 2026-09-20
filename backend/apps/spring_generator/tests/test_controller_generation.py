"""RED: apps.spring_generator.emit.context.ControllerContext and
build_controller_context do not exist yet.

Covers: DD45 (resource path segment via `naming.resource_path_segment`),
DD46 (exact six endpoint mappings/statuses, `@Valid @RequestBody` on
POST/PUT only), DD47 (`Pageable` bound directly, no custom
`@RequestParam` parsing). Templates rendered directly via the shared
Jinja `_ENVIRONMENT` (DD49) ahead of `generate_table_sources` wiring,
which Phase 7 adds.
"""
from apps.relational_mapping.domain.profile import ColumnProfile
from apps.relational_mapping.domain.schema import Column
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_controller_context
from apps.spring_generator.emit.renderer import _ENVIRONMENT
from apps.spring_generator.tests.factories import a_table, searchable


def _render(context):
    return _ENVIRONMENT.get_template("Controller.java.j2").render(
        package=context.package,
        class_name=context.class_name,
        service_field=context.service_field,
        service_type=context.service_type,
        request_dto=context.request_dto,
        response_dto=context.response_dto,
        resource_path=context.resource_path,
        list_parameters=context.list_parameters,
        list_arguments=context.list_arguments,
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


def test_controller_has_rest_controller_and_request_mapping():
    source = _render(build_controller_context(_product_table(), base_package="com.modelia.generated"))

    assert "@RestController" in source
    assert '@RequestMapping("/api/products")' in source


def test_controller_declares_all_six_required_endpoints():
    source = _render(build_controller_context(_product_table(), base_package="com.modelia.generated"))

    assert '@PostMapping("")' in source
    assert "@ResponseStatus(HttpStatus.CREATED)" in source
    assert 'public ProductResponseDto create(@Valid @RequestBody ProductRequestDto request) {' in source

    assert '@GetMapping("/{id}")' in source
    assert "public ProductResponseDto findById(@PathVariable UUID id) {" in source

    assert '@PutMapping("/{id}")' in source
    assert (
        "public ProductResponseDto update(@PathVariable UUID id, @Valid @RequestBody ProductRequestDto request) {"
        in source
    )

    assert '@DeleteMapping("/{id}")' in source
    assert "@ResponseStatus(HttpStatus.NO_CONTENT)" in source
    assert "public void delete(@PathVariable UUID id) {" in source

    assert '@GetMapping("")' in source
    assert "public Page<ProductResponseDto> list(Pageable pageable) {" in source

    assert '@GetMapping("/count")' in source
    assert "public long count() {" in source


def test_valid_request_body_only_on_post_and_put():
    source = _render(build_controller_context(_product_table(), base_package="com.modelia.generated"))

    assert source.count("@Valid @RequestBody") == 2


def test_pageable_bound_directly_no_request_param_for_paging():
    source = _render(build_controller_context(_product_table(), base_package="com.modelia.generated"))

    assert "Pageable pageable" in source
    assert "@RequestParam" not in source


def test_controller_references_only_dtos_never_the_entity_type():
    source = _render(build_controller_context(_product_table(), base_package="com.modelia.generated"))

    assert "ProductRequestDto" in source
    assert "ProductResponseDto" in source
    stripped = source.replace("ProductRequestDto", "").replace("ProductResponseDto", "")
    stripped = stripped.replace("ProductController", "").replace("ProductService", "")
    assert "Product" not in stripped


def test_order_line_table_yields_kebab_plural_path():
    table = a_table(name="order_line")
    context = build_controller_context(table, base_package="com.modelia.generated")

    assert context.resource_path == "/api/order-lines"


def test_braces_and_parens_are_balanced():
    source = _render(build_controller_context(_product_table(), base_package="com.modelia.generated"))

    assert source.count("{") == source.count("}")
    assert source.count("(") == source.count(")")


def test_searchable_fields_become_optional_typed_query_parameters():
    table = a_table(
        name="customer",
        columns=(
            Column(name="full_name", type=ColumnType.VARCHAR, profile=searchable()),
            Column(name="age", type=ColumnType.INTEGER, profile=searchable()),
        ),
    )

    source = _render(build_controller_context(table, base_package="com.modelia.generated"))

    assert "import org.springframework.web.bind.annotation.RequestParam;" in source
    assert "@RequestParam(required = false) String fullName" in source
    assert "@RequestParam(required = false) Integer age" in source
    assert "full_name" not in source
    assert "Pageable pageable" in source
    assert "return customerService.list(fullName, age, pageable);" in source


def test_numeric_big_decimal_query_parameter_import_is_conditional():
    table = a_table(name="order", columns=(Column(name="total", type=ColumnType.NUMERIC, profile=searchable()),))

    source = _render(build_controller_context(table, base_package="com.modelia.generated"))

    assert "import java.math.BigDecimal;" in source
    assert "@RequestParam(required = false) BigDecimal total" in source


def test_false_searchable_controller_matches_no_profile_output_byte_identical():
    plain = _render(build_controller_context(_product_table(), base_package="com.modelia.generated"))
    table = a_table(name="product", columns=(Column(name="name", type=ColumnType.VARCHAR, profile=ColumnProfile(searchable=False)),))

    profiled = _render(build_controller_context(table, base_package="com.modelia.generated"))

    assert profiled == plain
