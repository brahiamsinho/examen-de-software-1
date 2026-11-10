"""UML 2.5 Dependency: a "client" needs a "supplier". No multiplicity, no inheritance, no table."""
from apps.uml_commands.tests.factories import a_class, a_relationship, a_relationship_end
from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.validation.diagnostics import DiagnosticCode
from apps.uml_modeling.validation.engine import RULES, validate


def _codes(model) -> list[str]:
    return [item.code for item in validate(model, rules=RULES).diagnostics]


def test_dependency_is_one_of_the_relationship_kinds():
    assert RelationshipKind("dependency") is RelationshipKind.DEPENDENCY


def test_a_dependency_between_two_classes_is_valid():
    client, supplier = a_class(name="Pedido"), a_class(name="Calculadora")
    dependency = a_relationship(
        kind=RelationshipKind.DEPENDENCY,
        source=a_relationship_end(class_id=client.id),
        target=a_relationship_end(class_id=supplier.id),
    )
    model = CanonicalUmlModel(classes=(client, supplier), relationships=(dependency,))

    assert [code for code in _codes(model) if code != DiagnosticCode.CLASS_WITHOUT_ATTRIBUTES] == []


def test_a_class_may_depend_on_itself_unlike_a_self_association_which_is_only_warned_about():
    node = a_class(name="Nodo")
    dependency = a_relationship(
        kind=RelationshipKind.DEPENDENCY,
        source=a_relationship_end(class_id=node.id),
        target=a_relationship_end(class_id=node.id),
    )

    codes = _codes(CanonicalUmlModel(classes=(node,), relationships=(dependency,)))

    assert DiagnosticCode.SELF_ASSOCIATION not in codes


def test_a_dependency_to_a_class_that_does_not_exist_is_reported_like_any_other_relationship():
    client = a_class(name="Pedido")
    dependency = a_relationship(
        kind=RelationshipKind.DEPENDENCY, source=a_relationship_end(class_id=client.id)
    )

    codes = _codes(CanonicalUmlModel(classes=(client,), relationships=(dependency,)))

    assert DiagnosticCode.INVALID_RELATIONSHIP_ENDPOINT in codes


def test_a_dependency_is_not_inheritance_so_it_cannot_make_a_cycle_or_a_second_parent():
    a, b, c = a_class(name="A"), a_class(name="B"), a_class(name="C")
    ends = lambda s, t: dict(source=a_relationship_end(class_id=s.id), target=a_relationship_end(class_id=t.id))  # noqa: E731
    relationships = (
        a_relationship(kind=RelationshipKind.DEPENDENCY, **ends(a, b)),
        a_relationship(kind=RelationshipKind.DEPENDENCY, **ends(b, a)),
        a_relationship(kind=RelationshipKind.DEPENDENCY, **ends(a, c)),
    )

    codes = _codes(CanonicalUmlModel(classes=(a, b, c), relationships=relationships))

    assert DiagnosticCode.GENERALIZATION_CYCLE not in codes
    assert DiagnosticCode.MULTI_PARENT_GENERALIZATION not in codes
