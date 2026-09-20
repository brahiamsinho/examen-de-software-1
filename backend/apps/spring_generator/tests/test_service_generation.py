"""RED: apps.spring_generator.emit.context.ServiceContext/
RepositoryDependencyContext and build_service_context do not exist yet.

Covers: DD39 (six public methods, constructor injection, transaction
boundaries), DD40 (FK resolution via findById/orElseThrow, dedup,
self-reference, nullable-FK null guard), DD41/DD44 (ResourceNotFoundException
not-found contract, private conversion methods, no mapper library).
Templates rendered directly via the shared Jinja `_ENVIRONMENT` (DD49)
ahead of `generate_table_sources` wiring, which Phase 7 adds.
"""
from apps.relational_mapping.domain.profile import ColumnProfile, SortDirection
from apps.relational_mapping.domain.schema import Column
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_service_context
from apps.spring_generator.emit.renderer import _ENVIRONMENT
from apps.spring_generator.tests.factories import a_foreign_key, a_table, searchable, searchable_sortable, sortable, table_default_sort


def _render(context):
    return _ENVIRONMENT.get_template("Service.java.j2").render(
        package=context.package,
        class_name=context.class_name,
        entity_class=context.entity_class,
        repository_field=context.repository_field,
        repository_type=context.repository_type,
        dependencies=context.dependencies,
        constructor_parameters=context.constructor_parameters,
        constructor_assignments=context.constructor_assignments,
        list_support_fields=context.list_support_fields,
        list_parameters=context.list_parameters,
        list_statements=context.list_statements,
        list_support_methods=context.list_support_methods,
        to_response_statements=context.to_response_statements,
        apply_request_statements=context.apply_request_statements,
        resource_name=context.resource_name,
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


def test_service_has_service_annotation_and_no_component():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert "@Service" in source
    assert "@Component" not in source


def test_service_uses_constructor_injection_no_autowired():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert "private final ProductRepository productRepository;" in source
    assert "public ProductService(ProductRepository productRepository) {" in source
    assert "@Autowired" not in source


def test_service_declares_all_six_required_methods():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert "public ProductResponseDto create(ProductRequestDto request) {" in source
    assert "public ProductResponseDto findById(UUID id) {" in source
    assert "public ProductResponseDto update(UUID id, ProductRequestDto request) {" in source
    assert "public void delete(UUID id) {" in source
    assert "Page<ProductResponseDto> list(Pageable" in source
    assert "public long count() {" in source


def test_service_transaction_boundaries():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert "@Transactional(readOnly = true)" in source
    # Three mutators carry a plain @Transactional immediately before their signature.
    assert source.count("@Transactional\n    public") == 3


def test_service_not_found_contract_on_find_and_update():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert 'orElseThrow(() -> new ResourceNotFoundException("product", id));' in source


def test_service_delete_guards_with_exists_before_delete_by_id():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    exists_index = source.index("existsById(id)")
    delete_index = source.index("deleteById(id);")
    assert exists_index < delete_index
    assert "getReference" not in source


def test_service_conversion_methods_are_private():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert "private ProductResponseDto toResponseDto(Product entity) {" in source
    assert "private void applyRequestDto(Product entity, ProductRequestDto request) {" in source


def test_service_has_no_mapper_library_substring():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert "MapStruct" not in source
    assert "Mapper" not in source
    assert "BeanUtils" not in source


def test_service_dto_imports_present_despite_sub_package():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert "import com.modelia.generated.application.dto.ProductRequestDto;" in source
    assert "import com.modelia.generated.application.dto.ProductResponseDto;" in source


def test_fk_bearing_table_injects_related_repository_and_resolves_via_find_by_id():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        name="order",
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
    )

    context = build_service_context(table, base_package="com.modelia.generated")
    source = _render(context)

    assert "private final CategoryRepository categoryRepository;" in source
    assert "categoryRepository.findById(request.getCategoryId())" in source
    assert "getReference" not in source


def test_two_foreign_keys_to_same_table_inject_one_repository():
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

    context = build_service_context(table, base_package="com.modelia.generated")
    source = _render(context)

    assert source.count("private final AddressRepository addressRepository;") == 1
    assert "addressRepository.findById(request.getBillingAddressId())" in source
    assert "addressRepository.findById(request.getShippingAddressId())" in source


def test_self_referencing_foreign_key_injects_no_second_repository():
    fk = a_foreign_key(
        name="fk_category__parent_id", column_names=("parent_id",), referenced_table="category"
    )
    table = a_table(
        name="category",
        columns=(Column(name="parent_id", type=ColumnType.UUID, nullable=True),),
        foreign_keys=(fk,),
    )

    context = build_service_context(table, base_package="com.modelia.generated")
    source = _render(context)

    assert source.count("private final CategoryRepository categoryRepository;") == 1
    # Only one constructor parameter — the entity's own repository.
    assert "public CategoryService(CategoryRepository categoryRepository) {" in source


def test_nullable_foreign_key_emits_null_guard():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        name="order",
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=True),),
        foreign_keys=(fk,),
    )

    context = build_service_context(table, base_package="com.modelia.generated")
    source = _render(context)

    assert "if (request.getCategoryId() == null) {" in source
    assert "entity.setCategory(null);" in source


def test_braces_and_parens_are_balanced():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        name="order",
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=True),),
        foreign_keys=(fk,),
    )

    source = _render(build_service_context(table, base_package="com.modelia.generated"))

    assert source.count("{") == source.count("}")
    assert source.count("(") == source.count(")")


def test_searchable_table_service_uses_specification_find_all():
    table = a_table(
        name="customer",
        columns=(
            Column(name="full_name", type=ColumnType.VARCHAR, profile=searchable()),
            Column(name="age", type=ColumnType.INTEGER, profile=searchable()),
        ),
    )

    source = _render(build_service_context(table, base_package="com.modelia.generated"))

    assert "import org.springframework.data.jpa.domain.Specification;" in source
    assert "public Page<CustomerResponseDto> list(String fullName, Integer age, Pageable pageable)" in source
    assert "Pageable effectivePageable = normalizePageable(pageable);" in source
    assert "Specification<Customer> specification = CustomerSpecifications.byFilters(fullName, age);" in source
    assert "return customerRepository.findAll(specification, effectivePageable).map(this::toResponseDto);" in source


def test_no_profile_service_list_remains_byte_identical_to_existing_shape():
    source = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))

    assert "public Page<ProductResponseDto> list(Pageable pageable) {\n        return productRepository.findAll(pageable).map(this::toResponseDto);\n    }" in source
    assert "normalizePageable" not in source
    assert "Specification<Product>" not in source


def test_false_profile_service_matches_no_profile_output_byte_identical():
    plain = _render(build_service_context(_product_table(), base_package="com.modelia.generated"))
    table = a_table(name="product", columns=(Column(name="name", type=ColumnType.VARCHAR, profile=ColumnProfile(searchable=False, sortable=False)),))

    profiled = _render(build_service_context(table, base_package="com.modelia.generated"))

    assert profiled == plain


def test_service_generates_sortable_allow_list_and_rejects_invalid_sort():
    table = a_table(name="customer", columns=(Column(name="name", type=ColumnType.VARCHAR, profile=sortable()),))

    source = _render(build_service_context(table, base_package="com.modelia.generated"))

    assert "private static final Set<String> SORTABLE_FIELDS = Set.of(\"name\");" in source
    assert "for (Sort.Order order : pageable.getSort())" in source
    assert "if (!SORTABLE_FIELDS.contains(order.getProperty()))" in source
    assert 'throw new IllegalArgumentException("Unsupported sort property: " + order.getProperty());' in source
    assert "return customerRepository.findAll(effectivePageable).map(this::toResponseDto);" in source


def test_sort_validation_accepts_valid_sort_by_not_throwing_branch_for_allowed_field():
    table = a_table(name="customer", columns=(Column(name="name", type=ColumnType.VARCHAR, profile=sortable()),))

    source = _render(build_service_context(table, base_package="com.modelia.generated"))

    assert "SORTABLE_FIELDS.contains(order.getProperty())" in source
    assert "Set.of(\"name\")" in source


def test_default_sort_applies_only_when_pageable_unsorted():
    table = a_table(
        name="customer",
        columns=(Column(name="full_name", type=ColumnType.VARCHAR, source_element_id="name-id", profile=sortable()),),
        profile=table_default_sort("name-id", SortDirection.DESC),
    )

    source = _render(build_service_context(table, base_package="com.modelia.generated"))

    assert "if (pageable.getSort().isSorted()) {" in source
    assert "return pageable;" in source
    assert 'PageRequest.of(pageable.getPageNumber(), pageable.getPageSize(), Sort.by(Sort.Direction.DESC, "fullName"))' in source


def test_sort_validation_can_reject_any_sort_when_no_sortable_allow_list_exists():
    table = a_table(
        name="customer",
        columns=(Column(name="name", type=ColumnType.VARCHAR, profile=searchable()),),
    )

    source = _render(build_service_context(table, base_package="com.modelia.generated"))

    assert "private static final Set<String> SORTABLE_FIELDS = Set.of();" in source
    assert "if (!SORTABLE_FIELDS.contains(order.getProperty()))" in source
