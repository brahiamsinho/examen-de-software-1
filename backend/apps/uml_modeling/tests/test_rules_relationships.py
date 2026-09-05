"""RED: apps.uml_modeling.validation.rules.relationships does not exist yet."""
from apps.uml_modeling.domain.elements import RelationshipEnd, RelationshipKind
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.types import Multiplicity
from apps.uml_modeling.tests.factories import a_class, a_model, a_relationship
from apps.uml_modeling.validation.diagnostics import DiagnosticCode, ElementKind, Severity
from apps.uml_modeling.validation.rules.relationships import (
    generalization_cycle,
    invalid_relationship_endpoint,
    self_association,
)


def test_invalid_relationship_endpoint():
    order_class = a_class(name="Order")
    dangling_source_id = new_id()
    relationship = a_relationship(source_id=dangling_source_id, target_id=order_class.id)
    model = a_model(classes=(order_class,), relationships=(relationship,))

    diagnostics = invalid_relationship_endpoint(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.INVALID_RELATIONSHIP_ENDPOINT
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/relationships/{relationship.id}"
    assert diagnostic.element_ref.kind is ElementKind.RELATIONSHIP
    assert diagnostic.element_ref.id == relationship.id


def test_invalid_relationship_endpoint_flags_a_dangling_target_too():
    order_class = a_class(name="Order")
    dangling_target_id = new_id()
    relationship = a_relationship(source_id=order_class.id, target_id=dangling_target_id)
    model = a_model(classes=(order_class,), relationships=(relationship,))

    diagnostics = invalid_relationship_endpoint(model)

    assert len(diagnostics) == 1
    assert diagnostics[0].element_ref.id == relationship.id


def test_invalid_relationship_endpoint_produces_nothing_when_both_endpoints_resolve():
    order_class = a_class(name="Order")
    customer_class = a_class(name="Customer")
    relationship = a_relationship(source_id=order_class.id, target_id=customer_class.id)
    model = a_model(classes=(order_class, customer_class), relationships=(relationship,))

    assert invalid_relationship_endpoint(model) == ()


def _a_generalization(*, source_id, target_id):
    return a_relationship(
        kind=RelationshipKind.GENERALIZATION,
        source_id=source_id,
        target_id=target_id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(1, 1),
    )


def test_generalization_cycle_mutual_a_and_b():
    class_a = a_class(name="A")
    class_b = a_class(name="B")
    a_generalizes_b = _a_generalization(source_id=class_a.id, target_id=class_b.id)
    b_generalizes_a = _a_generalization(source_id=class_b.id, target_id=class_a.id)
    model = a_model(classes=(class_a, class_b), relationships=(a_generalizes_b, b_generalizes_a))

    diagnostics = generalization_cycle(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    expected_anchor = min(class_a.id, class_b.id)
    assert diagnostic.code is DiagnosticCode.GENERALIZATION_CYCLE
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/classes/{expected_anchor}"
    assert diagnostic.element_ref.id == expected_anchor


def test_generalization_cycle_self_generalization_is_a_length_one_cycle():
    class_a = a_class(name="A")
    self_generalization = _a_generalization(source_id=class_a.id, target_id=class_a.id)
    model = a_model(classes=(class_a,), relationships=(self_generalization,))

    diagnostics = generalization_cycle(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.GENERALIZATION_CYCLE
    assert diagnostic.element_ref.id == class_a.id
    assert diagnostic.code is not DiagnosticCode.SELF_ASSOCIATION


def test_generalization_cycle_produces_nothing_for_an_acyclic_hierarchy():
    parent = a_class(name="Parent")
    child = a_class(name="Child")
    child_generalizes_parent = _a_generalization(source_id=child.id, target_id=parent.id)
    model = a_model(classes=(parent, child), relationships=(child_generalizes_parent,))

    assert generalization_cycle(model) == ()


def test_self_association():
    order_class = a_class(name="Order")
    self_association_relationship = a_relationship(
        kind=RelationshipKind.ASSOCIATION,
        source_id=order_class.id,
        target_id=order_class.id,
    )
    model = a_model(classes=(order_class,), relationships=(self_association_relationship,))

    diagnostics = self_association(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.SELF_ASSOCIATION
    assert diagnostic.severity is Severity.WARNING
    assert diagnostic.path == f"/relationships/{self_association_relationship.id}"
    assert diagnostic.element_ref.kind is ElementKind.RELATIONSHIP


def test_self_association_does_not_flag_a_self_generalization():
    order_class = a_class(name="Order")
    self_generalization = _a_generalization(source_id=order_class.id, target_id=order_class.id)
    model = a_model(classes=(order_class,), relationships=(self_generalization,))

    assert self_association(model) == ()


def test_self_association_does_not_flag_a_regular_association():
    order_class = a_class(name="Order")
    customer_class = a_class(name="Customer")
    relationship = a_relationship(
        kind=RelationshipKind.ASSOCIATION, source_id=order_class.id, target_id=customer_class.id
    )
    model = a_model(classes=(order_class, customer_class), relationships=(relationship,))

    assert self_association(model) == ()
