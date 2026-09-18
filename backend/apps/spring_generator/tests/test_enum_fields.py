"""RED->GREEN: enum-typed column -> enum field generation on existing
entities (design.md DD28-DD29).

Covers: field type `pascal_case(enum_type_name)`; `@Enumerated(EnumType.STRING)`
present, `ORDINAL` never appears; fixed order `@Enumerated` -> `@Column`
-> `@NotNull` (DD11 extended); `@Size` never emitted on enum fields;
nullable enum column omits `@NotNull`; `Enumerated`/`EnumType` imports
conditional; an enum column does not raise through `java_type_for` in
either call site (DD28).
"""
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_entity_context
from apps.spring_generator.tests.factories import a_column, a_table


def test_enum_column_field_is_typed_pascal_case_of_enum_type_name():
    table = a_table(
        columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status", nullable=False),)
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "status")

    assert field.java_type == "OrderStatus"


def test_enum_column_field_carries_enumerated_string_annotation():
    table = a_table(columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status", nullable=False),))

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "status")

    assert "@Enumerated(EnumType.STRING)" in field.annotations
    assert not any("ORDINAL" in a for a in field.annotations)


def test_enum_field_annotation_order_is_enumerated_then_column_then_not_null():
    table = a_table(columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status", nullable=False),))

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "status")

    assert field.annotations[0] == "@Enumerated(EnumType.STRING)"
    assert field.annotations[1].startswith("@Column(")
    assert field.annotations[2] == "@NotNull"


def test_enum_field_never_carries_size_annotation():
    table = a_table(
        columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status", nullable=False, length=10),)
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "status")

    assert not any(a.startswith("@Size") for a in field.annotations)


def test_nullable_enum_column_omits_not_null():
    table = a_table(columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status", nullable=True),))

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "status")

    assert "@NotNull" not in field.annotations


def test_enumerated_and_enum_type_imports_are_conditional():
    plain_table = a_table()
    plain_context = build_entity_context(plain_table, base_package="com.modelia.generated")
    plain_fqns = {fqn for group in plain_context.import_groups for fqn in group}

    assert "jakarta.persistence.Enumerated" not in plain_fqns
    assert "jakarta.persistence.EnumType" not in plain_fqns

    enum_table = a_table(columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status"),))
    enum_context = build_entity_context(enum_table, base_package="com.modelia.generated")
    enum_fqns = {fqn for group in enum_context.import_groups for fqn in group}

    assert "jakarta.persistence.Enumerated" in enum_fqns
    assert "jakarta.persistence.EnumType" in enum_fqns


def test_enum_column_does_not_raise_through_java_type_for():
    table = a_table(columns=(a_column(name="status", type=ColumnType.ENUM, enum_type_name="order_status"),))

    # Would raise KeyError from javatypes.py if either call site (the
    # field builder or the import-collection loop) called
    # java_type_for on an ENUM column instead of short-circuiting on
    # enum_type_name (DD28).
    build_entity_context(table, base_package="com.modelia.generated")
