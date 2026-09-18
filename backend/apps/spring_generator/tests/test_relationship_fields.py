"""RED->GREEN: FK -> relationship field generation (design.md DD23-DD27).

Covers: plain FK -> @ManyToOne + @JoinColumn; FK matching a
UniqueConstraint -> @OneToOne + unique=true (DD24); self-referencing
FK generates its own class as field type with no import and no error
(DD27); two FKs to the same table produce two distinct field names
(DD26); a DD16-shaped join table (two single-column FKs, no PK-owned
column) generates two plain @ManyToOne fields with zero special-
casing; one field per column invariant (DD23/DD25); `referencedColumnName`
is never emitted; relationship imports are conditional;
`relationship_base_name` unit table.
"""
from apps.relational_mapping.domain.schema import Column
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.context import build_entity_context
from apps.spring_generator.emit.naming import relationship_base_name
from apps.spring_generator.tests.factories import a_foreign_key, a_table, a_unique_constraint


def test_plain_foreign_key_yields_many_to_one_join_column_field():
    fk = a_foreign_key(
        name="fk_product__category_id",
        column_names=("category_id",),
        referenced_table="category",
        referenced_column_names=("id",),
    )
    table = a_table(
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "category")

    assert field.java_type == "Category"
    assert field.annotations == (
        "@ManyToOne",
        '@JoinColumn(name = "category_id", nullable = false)',
        "@NotNull",
    )
    assert field.getter == "getCategory"
    assert field.setter == "setCategory"


def test_foreign_key_matching_unique_constraint_yields_one_to_one_field():
    fk = a_foreign_key(
        name="fk_profile__user_id",
        column_names=("user_id",),
        referenced_table="user",
        referenced_column_names=("id",),
    )
    uc = a_unique_constraint(name="uq_profile__user_id", column_names=("user_id",))
    table = a_table(
        name="profile",
        columns=(Column(name="user_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
        unique_constraints=(uc,),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "user")

    assert field.java_type == "User"
    assert field.annotations == (
        "@OneToOne",
        '@JoinColumn(name = "user_id", nullable = false, unique = true)',
        "@NotNull",
    )


def test_nullable_foreign_key_omits_not_null():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=True),),
        foreign_keys=(fk,),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "category")

    assert "@NotNull" not in field.annotations
    assert field.annotations[-1] == '@JoinColumn(name = "category_id", nullable = true)'


def test_non_nullable_foreign_key_carries_not_null():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "category")

    assert field.annotations[-1] == "@NotNull"


def test_self_referencing_foreign_key_generates_without_error_or_import():
    fk = a_foreign_key(
        name="fk_category__parent_id",
        column_names=("parent_id",),
        referenced_table="category",
        referenced_column_names=("id",),
    )
    table = a_table(
        name="category",
        columns=(Column(name="parent_id", type=ColumnType.UUID, nullable=True),),
        foreign_keys=(fk,),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    field = next(f for f in context.fields if f.name == "parent")

    assert field.java_type == "Category"
    for group in context.import_groups:
        for fqn in group:
            assert fqn != "com.modelia.generated.domain.Category"


def test_two_foreign_keys_to_the_same_table_yield_distinct_field_names():
    billing_fk = a_foreign_key(
        name="fk_order__billing_address_id",
        column_names=("billing_address_id",),
        referenced_table="address",
    )
    shipping_fk = a_foreign_key(
        name="fk_order__shipping_address_id",
        column_names=("shipping_address_id",),
        referenced_table="address",
    )
    table = a_table(
        name="order",
        columns=(
            Column(name="billing_address_id", type=ColumnType.UUID, nullable=False),
            Column(name="shipping_address_id", type=ColumnType.UUID, nullable=False),
        ),
        foreign_keys=(billing_fk, shipping_fk),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    field_names = {f.name for f in context.fields}

    assert "billingAddress" in field_names
    assert "shippingAddress" in field_names


def test_join_table_shape_yields_two_many_to_one_fields_with_no_special_casing():
    student_fk = a_foreign_key(name="fk_enrollment__student_id", column_names=("student_id",), referenced_table="student")
    course_fk = a_foreign_key(name="fk_enrollment__course_id", column_names=("course_id",), referenced_table="course")
    table = a_table(
        name="enrollment",
        columns=(
            Column(name="student_id", type=ColumnType.UUID, nullable=False),
            Column(name="course_id", type=ColumnType.UUID, nullable=False),
        ),
        foreign_keys=(student_fk, course_fk),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")
    relationship_fields = [f for f in context.fields if f.name in ("student", "course")]

    assert len(relationship_fields) == 2
    for field in relationship_fields:
        assert field.annotations[0] == "@ManyToOne"
        assert not any("ManyToMany" in a or "JoinTable" in a for a in field.annotations)


def test_relationship_field_has_no_column_annotation_and_field_count_matches_columns():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")

    assert len(context.fields) == len(table.columns)
    relationship_field = next(f for f in context.fields if f.name == "category")
    assert not any(a.startswith("@Column") for a in relationship_field.annotations)


def test_referenced_column_name_is_never_emitted():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category", referenced_column_names=("id",))
    table = a_table(
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")

    for field in context.fields:
        for annotation in field.annotations:
            assert "referencedColumnName" not in annotation


def test_relationship_imports_are_conditional():
    plain_table = a_table()
    context = build_entity_context(plain_table, base_package="com.modelia.generated")
    all_fqns = {fqn for group in context.import_groups for fqn in group}

    assert "jakarta.persistence.ManyToOne" not in all_fqns
    assert "jakarta.persistence.OneToOne" not in all_fqns
    assert "jakarta.persistence.JoinColumn" not in all_fqns

    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    fk_table = a_table(
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
    )
    fk_context = build_entity_context(fk_table, base_package="com.modelia.generated")
    fk_fqns = {fqn for group in fk_context.import_groups for fqn in group}

    assert "jakarta.persistence.ManyToOne" in fk_fqns
    assert "jakarta.persistence.JoinColumn" in fk_fqns
    assert "jakarta.persistence.OneToOne" not in fk_fqns


def test_base_package_import_group_stays_empty_for_relationship_fields():
    fk = a_foreign_key(column_names=("category_id",), referenced_table="category")
    table = a_table(
        columns=(Column(name="category_id", type=ColumnType.UUID, nullable=False),),
        foreign_keys=(fk,),
    )

    context = build_entity_context(table, base_package="com.modelia.generated")

    for group in context.import_groups:
        for fqn in group:
            assert not fqn.startswith("com.modelia.generated.")


def test_relationship_base_name_strips_trailing_id_suffix():
    assert relationship_base_name("category_id") == "category"


def test_relationship_base_name_handles_reserved_word_suffix():
    assert relationship_base_name("class_id") == "class"


def test_relationship_base_name_leaves_unsuffixed_name_unchanged():
    assert relationship_base_name("owner") == "owner"


def test_relationship_base_name_leaves_bare_id_column_unchanged():
    assert relationship_base_name("id") == "id"
