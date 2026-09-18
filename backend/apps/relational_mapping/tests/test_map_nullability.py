"""RED: mapper does not implement FK nullability rules yet (Stage 4)."""
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import a_class, a_composition, a_model, an_association
from apps.uml_modeling.domain.types import Multiplicity


def _fk_column_for(result, table_name):
    table = result.table_by_name(table_name)
    fk = table.foreign_keys[0]
    return table.column_by_name(fk.column_names[0])


def test_optional_referenced_end_produces_nullable_fk():
    customer = a_class(name="Customer")
    order = a_class(name="Order")
    relationship = an_association(
        source_id=customer.id,
        target_id=order.id,
        source_multiplicity=Multiplicity(0, 1),
        target_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(customer, order), relationships=(relationship,))

    result = map_to_relational(model)

    assert _fk_column_for(result, "order").nullable is True


def test_mandatory_referenced_end_produces_not_null_fk():
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

    assert _fk_column_for(result, "order").nullable is False


def test_negative_lower_bound_behaves_as_optional():
    customer = a_class(name="Customer")
    order = a_class(name="Order")
    relationship = an_association(
        source_id=customer.id,
        target_id=order.id,
        source_multiplicity=Multiplicity(-1, 1),
        target_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(customer, order), relationships=(relationship,))

    result = map_to_relational(model)

    assert _fk_column_for(result, "order").nullable is True


def test_composition_fk_is_not_null_even_at_zero_lower_bound():
    order = a_class(name="Order")
    order_line = a_class(name="OrderLine")
    composition = a_composition(
        whole_id=order.id,
        part_id=order_line.id,
        whole_multiplicity=Multiplicity(0, 1),
        part_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(order, order_line), relationships=(composition,))

    result = map_to_relational(model)

    assert _fk_column_for(result, "order_line").nullable is False
