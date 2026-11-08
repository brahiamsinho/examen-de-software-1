from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.preview import relational_preview, relational_sql
from apps.relational_mapping.tests.factories import a_class, a_model, an_association
from apps.uml_modeling.domain.types import Multiplicity


def test_sql_is_deterministic_and_emits_primary_and_foreign_keys():
    customer = a_class(name="Customer")
    order = a_class(name="Order")
    model = a_model(
        classes=(customer, order),
        relationships=(
            an_association(
                source_id=customer.id,
                target_id=order.id,
                source_multiplicity=Multiplicity(1, 1),
                target_multiplicity=Multiplicity(0, None),
            ),
        ),
    )
    relational = map_to_relational(model)

    first = relational_sql(relational)

    assert first == relational_sql(relational)
    assert 'CONSTRAINT "pk_customer" PRIMARY KEY ("id")' in first
    assert 'FOREIGN KEY ("customer_id") REFERENCES "customer" ("id")' in first
    assert relational_preview(relational)["tables"][1]["foreign_keys"][0]["referenced_table"] == "customer"
