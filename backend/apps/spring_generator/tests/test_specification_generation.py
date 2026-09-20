from apps.relational_mapping.domain.schema import Column
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_specification_context
from apps.spring_generator.emit.renderer import _ENVIRONMENT, generate_table_sources
from apps.spring_generator.tests.factories import a_table, searchable


def _render(table):
    context = build_specification_context(table, base_package="com.modelia.generated")
    return _ENVIRONMENT.get_template("Specifications.java.j2").render(
        package=context.package,
        class_name=context.class_name,
        entity_class=context.entity_class,
        filters=context.filters,
        import_groups=context.import_groups,
    )


def test_string_filters_use_case_insensitive_contains_and_skip_blank_values():
    table = a_table(
        name="customer",
        columns=(
            Column(name="full_name", type=ColumnType.VARCHAR, profile=searchable()),
            Column(name="notes", type=ColumnType.TEXT, profile=searchable()),
        ),
    )

    source = _render(table)

    assert "public static Specification<Customer> byFilters(String fullName, String notes)" in source
    assert "fullName != null && !fullName.isBlank()" in source
    assert 'criteriaBuilder.lower(root.get("fullName"))' in source
    assert '"%" + fullName.toLowerCase() + "%"' in source
    assert 'criteriaBuilder.lower(root.get("notes"))' in source


def test_numeric_filters_use_exact_equality_with_typed_parameters():
    table = a_table(
        name="order",
        columns=(
            Column(name="age", type=ColumnType.INTEGER, profile=searchable()),
            Column(name="rank", type=ColumnType.BIGINT, profile=searchable()),
            Column(name="total", type=ColumnType.NUMERIC, profile=searchable()),
        ),
    )

    source = _render(table)

    assert "import java.math.BigDecimal;" in source
    assert "public static Specification<Order> byFilters(Integer age, Long rank, BigDecimal total)" in source
    assert 'criteriaBuilder.equal(root.get("age"), age)' in source
    assert 'criteriaBuilder.equal(root.get("rank"), rank)' in source
    assert 'criteriaBuilder.equal(root.get("total"), total)' in source


def test_multiple_filters_are_combined_with_and_and_no_unsupported_operators():
    table = a_table(
        name="customer",
        columns=(
            Column(name="name", type=ColumnType.VARCHAR, profile=searchable()),
            Column(name="age", type=ColumnType.INTEGER, profile=searchable()),
        ),
    )

    source = _render(table)

    assert "criteriaBuilder.and(predicates.toArray(new Predicate[0]))" in source
    assert "criteriaBuilder.conjunction()" in source
    for unsupported in ("criteriaBuilder.or", "greaterThan", "lessThan", "between", "not("):
        assert unsupported not in source


def test_generate_table_sources_emits_single_specification_file_for_searchable_table():
    table = a_table(name="customer", columns=(Column(name="name", type=ColumnType.VARCHAR, profile=searchable()),))

    sources = generate_table_sources(table, base_package="com.modelia.generated")
    paths = tuple(generated_file.path for generated_file in sources.files)

    assert paths.count("src/main/java/com/modelia/generated/application/CustomerSpecifications.java") == 1
