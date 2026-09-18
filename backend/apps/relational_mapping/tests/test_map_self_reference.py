"""RED: mapper does not implement self-reference handling yet (Stage 4)."""
from apps.relational_mapping.domain.types import ReferentialAction
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import a_class, a_composition, a_model, an_association
from apps.uml_modeling.domain.types import Multiplicity


def test_self_association_produces_a_self_fk_on_the_same_table():
    employee = a_class(name="Employee")
    manages = an_association(
        source_id=employee.id,
        target_id=employee.id,
        source_multiplicity=Multiplicity(0, 1),
        target_multiplicity=Multiplicity(0, None),
        source_role="manager",
    )
    model = a_model(classes=(employee,), relationships=(manages,))

    result = map_to_relational(model)

    assert len(result.tables) == 1
    table = result.tables[0]
    fk_column = table.column_by_name("manager_id")
    assert fk_column is not None
    assert fk_column.nullable is True
    assert table.foreign_keys[0].referenced_table == "employee"


def test_self_composition_fk_is_nullable_with_cascade():
    node = a_class(name="Node")
    composition = a_composition(
        whole_id=node.id,
        part_id=node.id,
        whole_multiplicity=Multiplicity(0, 1),
        part_multiplicity=Multiplicity(0, None),
        whole_role="parent",
    )
    model = a_model(classes=(node,), relationships=(composition,))

    result = map_to_relational(model)

    table = result.tables[0]
    fk_column = table.column_by_name("parent_id")
    assert fk_column.nullable is True
    assert table.foreign_keys[0].on_delete is ReferentialAction.CASCADE


def test_self_many_to_many_produces_a_join_table_with_two_disambiguated_fks():
    employee = a_class(name="Employee")
    collaborates = an_association(
        source_id=employee.id,
        target_id=employee.id,
        source_multiplicity=Multiplicity(0, None),
        target_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(employee,), relationships=(collaborates,))

    result = map_to_relational(model)

    join_table = result.table_by_name("employee_employee")
    assert join_table is not None
    fk_column_names = {fk.column_names[0] for fk in join_table.foreign_keys}
    assert len(fk_column_names) == 2
    for fk in join_table.foreign_keys:
        assert fk.referenced_table == "employee"
