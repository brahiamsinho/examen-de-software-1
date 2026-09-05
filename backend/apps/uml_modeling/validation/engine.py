"""The single validation entry point, reused by every future caller
(saving, import, collaboration, assistant, generation flows).

The registry is an explicit static tuple (DD4) rather than a decorator
auto-registry: deterministic order, no import-time side effects, no
hidden global mutable state, and the registry itself is assertable in
a test ("exactly 10 rules", Phase 7.6).
"""
from collections.abc import Callable, Iterable

from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.validation.diagnostics import Diagnostic, ValidationResult
from apps.uml_modeling.validation.rules.multiplicity import invalid_multiplicity
from apps.uml_modeling.validation.rules.naming import (
    duplicate_attribute_name,
    duplicate_class_name,
    duplicate_enumeration_literal,
    empty_element_name,
)
from apps.uml_modeling.validation.rules.relationships import (
    generalization_cycle,
    invalid_relationship_endpoint,
    self_association,
)
from apps.uml_modeling.validation.rules.structure import class_without_attributes
from apps.uml_modeling.validation.rules.types import unknown_attribute_type

Rule = Callable[[CanonicalUmlModel], Iterable[Diagnostic]]

# The complete Cycle-1 registry: exactly the 10 fixed rules (uml-validation
# spec), in declared order (DD4). `test_registry_has_exactly_ten_rules`
# (Phase 7.6) asserts this count.
RULES: tuple[Rule, ...] = (
    empty_element_name,
    duplicate_class_name,
    duplicate_attribute_name,
    duplicate_enumeration_literal,
    unknown_attribute_type,
    invalid_relationship_endpoint,
    invalid_multiplicity,
    generalization_cycle,
    self_association,
    class_without_attributes,
)


def validate(model: CanonicalUmlModel, rules: tuple[Rule, ...] = RULES) -> ValidationResult:
    """Run every rule against `model` and aggregate all diagnostics.

    Never short-circuits: every rule runs and contributes its
    diagnostics, regardless of what earlier rules found.
    """
    diagnostics: list[Diagnostic] = []
    for rule in rules:
        diagnostics.extend(rule(model))
    return ValidationResult(diagnostics=tuple(diagnostics))
