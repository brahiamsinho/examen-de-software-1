"""A class that only has a dependency takes part in a relationship: it is not "isolated"."""
from apps.architecture_audit import analyzer
from apps.uml_commands.tests.factories import a_class, a_relationship, a_relationship_end
from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.model import CanonicalUmlModel


def test_a_class_connected_only_by_a_dependency_is_not_reported_as_isolated():
    client, supplier = a_class(name="Pedido"), a_class(name="Calculadora")
    dependency = a_relationship(
        kind=RelationshipKind.DEPENDENCY,
        source=a_relationship_end(class_id=client.id),
        target=a_relationship_end(class_id=supplier.id),
    )

    findings = analyzer.audit(CanonicalUmlModel(classes=(client, supplier), relationships=(dependency,)))

    assert "AR-001" not in {finding.rule_id for finding in findings}


def test_without_the_dependency_the_same_two_classes_are_isolated():
    findings = analyzer.audit(CanonicalUmlModel(classes=(a_class(name="Pedido"), a_class(name="Calculadora"))))

    assert "AR-001" in {finding.rule_id for finding in findings}
