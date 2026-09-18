"""RED: mapper does not implement relationship mapping yet (Stage 4)."""
from apps.relational_mapping.domain.types import ColumnType, ReferentialAction
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import (
    a_class,
    a_composition,
    a_generalization,
    a_model,
    an_association,
)
from apps.uml_modeling.domain.types import Multiplicity


def test_one_to_one_association_puts_fk_on_target_with_unique_constraint():
    person = a_class(name="Person")
    passport = a_class(name="Passport")
    relationship = an_association(
        source_id=person.id,
        target_id=passport.id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(1, 1),
    )
    model = a_model(classes=(person, passport), relationships=(relationship,))

    result = map_to_relational(model)

    passport_table = result.table_by_name("passport")
    fk_column = passport_table.column_by_name("person_id")
    assert fk_column is not None
    assert fk_column.type is ColumnType.UUID
    assert passport_table.unique_constraints[0].column_names == ("person_id",)
    assert passport_table.foreign_keys[0].referenced_table == "person"
    # No redundant index behind the unique constraint (DD17)
    assert passport_table.indexes == ()


def test_one_to_many_association_puts_fk_on_the_many_side():
    customer = a_class(name="Customer")
    order = a_class(name="Order")
    relationship = an_association(
        source_id=customer.id,
        target_id=order.id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(customer, order), relationships=(relationship,))

    result = map_to_relational(model)

    order_table = result.table_by_name("order")
    fk_column = order_table.column_by_name("customer_id")
    assert fk_column is not None
    assert order_table.foreign_keys[0].referenced_table == "customer"
    assert result.table_by_name("customer").column_by_name("order_id") is None
    assert order_table.indexes[0].column_names == ("customer_id",)
    assert len(result.tables) == 2


def test_many_to_many_association_produces_a_join_table():
    student = a_class(name="Student")
    course = a_class(name="Course")
    relationship = an_association(
        source_id=student.id,
        target_id=course.id,
        source_multiplicity=Multiplicity(0, None),
        target_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(student, course), relationships=(relationship,))

    result = map_to_relational(model)

    join_table = result.table_by_name("student_course")
    assert join_table is not None
    assert join_table.primary_key.column_names == ("id",)
    assert join_table.primary_key.name == "pk_student_course"
    referenced_tables = {fk.referenced_table for fk in join_table.foreign_keys}
    assert referenced_tables == {"student", "course"}
    assert len(join_table.unique_constraints) == 1
    assert len(join_table.indexes) == 2
    assert len(result.tables) == 3


def test_role_based_fk_naming():
    employee = a_class(name="Employee")
    department = a_class(name="Department")
    relationship = an_association(
        source_id=department.id,
        target_id=employee.id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(0, None),
        source_role="employer",
    )
    model = a_model(classes=(department, employee), relationships=(relationship,))

    result = map_to_relational(model)

    employee_table = result.table_by_name("employee")
    assert employee_table.column_by_name("employer_id") is not None
    assert employee_table.column_by_name("department_id") is None


def test_two_relationships_between_the_same_pair_get_distinct_fk_columns():
    order = a_class(name="Order")
    customer = a_class(name="Customer")
    billing = an_association(
        source_id=customer.id,
        target_id=order.id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(0, None),
        source_role="billing_customer",
    )
    shipping = an_association(
        source_id=customer.id,
        target_id=order.id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(0, None),
        source_role="shipping_customer",
    )
    model = a_model(classes=(customer, order), relationships=(billing, shipping))

    result = map_to_relational(model)

    order_table = result.table_by_name("order")
    assert order_table.column_by_name("billing_customer_id") is not None
    assert order_table.column_by_name("shipping_customer_id") is not None


def test_composition_fk_is_not_null_cascade():
    order = a_class(name="Order")
    order_line = a_class(name="OrderLine")
    composition = a_composition(
        whole_id=order.id,
        part_id=order_line.id,
        whole_multiplicity=Multiplicity(1, 1),
        part_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(order, order_line), relationships=(composition,))

    result = map_to_relational(model)

    order_line_table = result.table_by_name("order_line")
    fk = order_line_table.foreign_keys[0]
    fk_column = order_line_table.column_by_name(fk.column_names[0])
    assert fk_column.nullable is False
    assert fk.on_delete is ReferentialAction.CASCADE


def test_generalization_relationship_produces_no_fk_or_join_table():
    vehicle = a_class(name="Vehicle")
    car = a_class(name="Car")
    generalization = a_generalization(source_id=car.id, target_id=vehicle.id)
    model = a_model(classes=(vehicle, car), relationships=(generalization,))

    result = map_to_relational(model)

    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.foreign_keys == ()


def test_fk_to_a_subclass_lands_on_the_hierarchy_root_table():
    vehicle = a_class(name="Vehicle")
    car = a_class(name="Car")
    generalization = a_generalization(source_id=car.id, target_id=vehicle.id)
    owner = a_class(name="Owner")
    owns = an_association(
        source_id=owner.id,
        target_id=car.id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(vehicle, car, owner), relationships=(generalization, owns))

    result = map_to_relational(model)

    vehicle_table = result.table_by_name("vehicle")
    assert vehicle_table.column_by_name("owner_id") is not None
    assert len(result.tables) == 2
