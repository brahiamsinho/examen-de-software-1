from apps.architecture_audit.analyzer import audit, report
from apps.architecture_audit.exports import markdown
from apps.uml_modeling.domain.elements import Relationship, RelationshipEnd, RelationshipKind, UmlAttribute, UmlClass, UmlOperation
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity, PrimitiveType


def _class(class_id: str, *, attributes: int = 0, operations: int = 0) -> UmlClass:
    return UmlClass(
        id=ElementId(class_id),
        name=class_id.title(),
        attributes=tuple(UmlAttribute(ElementId(f"{class_id}-a{index}"), f"a{index}", PrimitiveType.STRING) for index in range(attributes)),
        operations=tuple(UmlOperation(ElementId(f"{class_id}-o{index}"), f"o{index}") for index in range(operations)),
    )


def _relationship(relationship_id: str, source: str, target: str, kind: RelationshipKind = RelationshipKind.ASSOCIATION) -> Relationship:
    one = Multiplicity(1, 1)
    return Relationship(
        id=ElementId(relationship_id), kind=kind,
        source=RelationshipEnd(ElementId(source), one), target=RelationshipEnd(ElementId(target), one),
    )


def test_audit_detects_each_documented_rule_with_real_element_ids():
    classes = (_class("isolated"), _class("hub"), _class("large", attributes=6, operations=4), *(_class(f"n{index}") for index in range(5)), *(_class(f"h{index}") for index in range(5)))
    relationships = (
        *(_relationship(f"hub-{index}", "hub", f"n{index}") for index in range(5)),
        _relationship("h1", "h0", "h1", RelationshipKind.GENERALIZATION),
        _relationship("h2", "h1", "h2", RelationshipKind.GENERALIZATION),
        _relationship("h3", "h2", "h3", RelationshipKind.GENERALIZATION),
        _relationship("h4", "h3", "h4", RelationshipKind.GENERALIZATION),
        _relationship("cycle-a", "n0", "n1"),
        _relationship("cycle-b", "n1", "n0"),
    )

    findings = audit(CanonicalUmlModel(classes=classes, relationships=relationships))

    assert {finding.rule_id for finding in findings} == {"AR-001", "AR-002", "AR-003", "AR-004", "AR-005"}
    assert all(set(finding.element_ids) <= {str(uml_class.id) for uml_class in classes} for finding in findings)
    assert {finding.severity for finding in findings} == {"INFO", "WARNING"}


def test_audit_has_no_findings_for_a_small_connected_model():
    model = CanonicalUmlModel(classes=(_class("a"), _class("b")), relationships=(_relationship("r", "a", "b"),))

    assert audit(model) == ()


def test_report_is_deterministic_and_ignores_input_order():
    classes = (_class("a"), _class("b"))
    relationships = (_relationship("ab", "a", "b"), _relationship("ba", "b", "a"))
    first = report(CanonicalUmlModel(classes=classes, relationships=relationships), document_id="document", revision=7)
    second = report(CanonicalUmlModel(classes=tuple(reversed(classes)), relationships=tuple(reversed(relationships))), document_id="document", revision=7)

    assert first == second
    assert markdown(first) == markdown(second)
    assert "202" not in markdown(first)
