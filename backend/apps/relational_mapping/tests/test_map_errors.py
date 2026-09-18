"""RED: apps.relational_mapping.mapping.mapper does not exist yet.

Errors are the mapper's second line of defense (DD18) for the
structures it cannot represent: multi-parent generalization,
generalization cycles, and dangling relationship endpoints. All
subclass `UnmappableModelError`.
"""
import pytest

from apps.relational_mapping.mapping.errors import (
    DanglingRelationshipEndpointError,
    GeneralizationCycleError,
    MultipleGeneralizationParentsError,
    UnmappableModelError,
)
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import a_class, a_generalization, a_model, an_association
from apps.uml_modeling.domain.ids import new_id


def test_multi_parent_generalization_raises():
    child = a_class(name="Car")
    parent_a = a_class(name="Vehicle")
    parent_b = a_class(name="Machine")
    to_a = a_generalization(source_id=child.id, target_id=parent_a.id)
    to_b = a_generalization(source_id=child.id, target_id=parent_b.id)
    model = a_model(classes=(child, parent_a, parent_b), relationships=(to_a, to_b))

    with pytest.raises(MultipleGeneralizationParentsError) as excinfo:
        map_to_relational(model)

    assert issubclass(MultipleGeneralizationParentsError, UnmappableModelError)
    assert excinfo.value.class_id == child.id
    assert set(excinfo.value.parent_ids) == {parent_a.id, parent_b.id}


def test_generalization_cycle_raises_and_terminates():
    class_a = a_class(name="A")
    class_b = a_class(name="B")
    a_to_b = a_generalization(source_id=class_a.id, target_id=class_b.id)
    b_to_a = a_generalization(source_id=class_b.id, target_id=class_a.id)
    model = a_model(classes=(class_a, class_b), relationships=(a_to_b, b_to_a))

    with pytest.raises(GeneralizationCycleError) as excinfo:
        map_to_relational(model)

    assert issubclass(GeneralizationCycleError, UnmappableModelError)
    assert set(excinfo.value.class_ids) == {class_a.id, class_b.id}


def test_dangling_relationship_endpoint_raises():
    order = a_class(name="Order")
    dangling_target_id = new_id()
    relationship = an_association(source_id=order.id, target_id=dangling_target_id)
    model = a_model(classes=(order,), relationships=(relationship,))

    with pytest.raises(DanglingRelationshipEndpointError) as excinfo:
        map_to_relational(model)

    assert issubclass(DanglingRelationshipEndpointError, UnmappableModelError)
    assert excinfo.value.relationship_id == relationship.id


def test_no_error_raised_for_a_valid_single_parent_model():
    parent = a_class(name="Vehicle")
    child = a_class(name="Car")
    generalization = a_generalization(source_id=child.id, target_id=parent.id)
    model = a_model(classes=(parent, child), relationships=(generalization,))

    # Should not raise — single-parent, acyclic, no dangling endpoints.
    map_to_relational(model)
