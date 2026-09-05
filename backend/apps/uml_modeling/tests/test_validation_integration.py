"""Integration test (uml-validation REQ4): every diagnostic's path and
element_ref MUST resolve to an element actually present in the
validated model, across the full 10-rule registry, exercised together
via `validate()` (not each rule in isolation).
"""
from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity
from apps.uml_modeling.tests.factories import (
    a_class,
    an_attribute,
    an_enumeration,
    an_enumeration_literal,
    a_model,
    a_relationship,
    diagnostic_resolves_to_a_real_element,
)
from apps.uml_modeling.validation.diagnostics import DiagnosticCode
from apps.uml_modeling.validation.engine import validate


def test_every_diagnostic_from_the_full_registry_resolves_to_a_real_element():
    empty_class = a_class(name="")
    order = a_class(name="Order", attributes=(an_attribute(name="id"),))
    duplicate_order = a_class(name="Order", attributes=(an_attribute(name="id"),))
    item = a_class(name="Item", attributes=(an_attribute(name="qty"), an_attribute(name="qty")))
    widget = a_class(
        name="Widget", attributes=(an_attribute(name="status", type=EnumerationRef(new_id())),)
    )
    status_enum = an_enumeration(
        name="Status",
        literals=(an_enumeration_literal(name="ACTIVE"), an_enumeration_literal(name="ACTIVE")),
    )

    self_association = a_relationship(
        kind=RelationshipKind.ASSOCIATION, source_id=order.id, target_id=order.id
    )
    self_generalization = a_relationship(
        kind=RelationshipKind.GENERALIZATION,
        source_id=order.id,
        target_id=order.id,
        source_multiplicity=Multiplicity(1, 1),
        target_multiplicity=Multiplicity(1, 1),
    )
    dangling_relationship = a_relationship(source_id=new_id(), target_id=order.id)
    invalid_multiplicity_relationship = a_relationship(
        source_id=order.id,
        target_id=duplicate_order.id,
        source_multiplicity=Multiplicity(-1, None),
    )

    model = a_model(
        classes=(empty_class, order, duplicate_order, item, widget),
        enumerations=(status_enum,),
        relationships=(
            self_association,
            self_generalization,
            dangling_relationship,
            invalid_multiplicity_relationship,
        ),
    )

    result = validate(model)

    produced_codes = {diagnostic.code for diagnostic in result.diagnostics}
    assert produced_codes == set(DiagnosticCode)
    assert len(result.diagnostics) == 10

    for diagnostic in result.diagnostics:
        assert diagnostic_resolves_to_a_real_element(model, diagnostic), (
            f"{diagnostic.code} at {diagnostic.path} does not resolve to a real element"
        )
