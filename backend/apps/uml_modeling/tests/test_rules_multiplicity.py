"""RED: apps.uml_modeling.validation.rules.multiplicity does not exist yet."""
from apps.uml_modeling.domain.types import Multiplicity
from apps.uml_modeling.tests.factories import a_class, a_model, a_relationship
from apps.uml_modeling.validation.diagnostics import DiagnosticCode, ElementKind, Severity
from apps.uml_modeling.validation.rules.multiplicity import invalid_multiplicity


def test_invalid_multiplicity_negative_lower():
    order_class = a_class(name="Order")
    customer_class = a_class(name="Customer")
    relationship = a_relationship(
        source_id=order_class.id,
        target_id=customer_class.id,
        source_multiplicity=Multiplicity(-1, None),
    )
    model = a_model(classes=(order_class, customer_class), relationships=(relationship,))

    diagnostics = invalid_multiplicity(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.INVALID_MULTIPLICITY
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/relationships/{relationship.id}"
    assert diagnostic.element_ref.kind is ElementKind.RELATIONSHIP
    assert diagnostic.element_ref.id == relationship.id


def test_invalid_multiplicity_upper_below_lower():
    order_class = a_class(name="Order")
    customer_class = a_class(name="Customer")
    relationship = a_relationship(
        source_id=order_class.id,
        target_id=customer_class.id,
        target_multiplicity=Multiplicity(2, 1),
    )
    model = a_model(classes=(order_class, customer_class), relationships=(relationship,))

    diagnostics = invalid_multiplicity(model)

    assert len(diagnostics) == 1
    assert diagnostics[0].code is DiagnosticCode.INVALID_MULTIPLICITY


def test_invalid_multiplicity_produces_nothing_for_valid_ranges():
    order_class = a_class(name="Order")
    customer_class = a_class(name="Customer")
    relationship = a_relationship(
        source_id=order_class.id,
        target_id=customer_class.id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(0, None),
    )
    model = a_model(classes=(order_class, customer_class), relationships=(relationship,))

    assert invalid_multiplicity(model) == ()
