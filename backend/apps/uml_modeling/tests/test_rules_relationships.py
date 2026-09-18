"""RED: apps.uml_modeling.validation.rules.relationships does not exist yet."""
from apps.uml_modeling.domain.elements import RelationshipEnd, RelationshipKind
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.types import Multiplicity
from apps.uml_modeling.tests.factories import a_class, a_model, a_relationship
from apps.uml_modeling.validation.diagnostics import DiagnosticCode, ElementKind, Severity
from apps.uml_modeling.validation.rules.relationships import (
    generalization_cycle,
    invalid_relationship_endpoint,
    multi_parent_generalization,
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


def test_multi_parent_generalization_fires_on_two_distinct_parents():
    child = a_class(name="Car")
    parent_a = a_class(name="Vehicle")
    parent_b = a_class(name="Machine")
    to_a = _a_generalization(source_id=child.id, target_id=parent_a.id)
    to_b = _a_generalization(source_id=child.id, target_id=parent_b.id)
    model = a_model(classes=(child, parent_a, parent_b), relationships=(to_a, to_b))

    diagnostics = multi_parent_generalization(model)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code is DiagnosticCode.MULTI_PARENT_GENERALIZATION
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.path == f"/classes/{child.id}"
    assert diagnostic.element_ref.kind is ElementKind.CLASS
    assert diagnostic.element_ref.id == child.id


def test_multi_parent_generalization_is_silent_on_a_single_parent():
    child = a_class(name="Car")
    parent = a_class(name="Vehicle")
    to_parent = _a_generalization(source_id=child.id, target_id=parent.id)
    model = a_model(classes=(child, parent), relationships=(to_parent,))

    assert multi_parent_generalization(model) == ()


def test_multi_parent_generalization_is_silent_on_a_duplicate_edge_to_the_same_parent():
    child = a_class(name="Car")
    parent = a_class(name="Vehicle")
    first_edge = _a_generalization(source_id=child.id, target_id=parent.id)
    duplicate_edge = _a_generalization(source_id=child.id, target_id=parent.id)
    model = a_model(classes=(child, parent), relationships=(first_edge, duplicate_edge))

    assert multi_parent_generalization(model) == ()


def test_multi_parent_generalization_order_is_deterministic_by_model_classes_order():
    child_one = a_class(name="Car")
    child_two = a_class(name="Boat")
    parent_a = a_class(name="Vehicle")
    parent_b = a_class(name="Machine")
    relationships = (
        _a_generalization(source_id=child_one.id, target_id=parent_a.id),
        _a_generalization(source_id=child_one.id, target_id=parent_b.id),
        _a_generalization(source_id=child_two.id, target_id=parent_a.id),
        _a_generalization(source_id=child_two.id, target_id=parent_b.id),
    )
    model = a_model(classes=(child_one, child_two, parent_a, parent_b), relationships=relationships)

    diagnostics = multi_parent_generalization(model)

    assert [d.element_ref.id for d in diagnostics] == [child_one.id, child_two.id]
