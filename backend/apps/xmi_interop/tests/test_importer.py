"""Importer behaviour: the real EA sample, EA constructs beyond it, XMI 2.1, failures."""
import pathlib

import pytest

from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity, PrimitiveType
from apps.xmi_interop.errors import InvalidXmiError, UnsupportedXmiError
from apps.xmi_interop.importer import MAX_XMI_BYTES, import_xmi

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _by_name(model, name):
    return next(c for c in model.classes if c.name == name)


def _attrs(uml_class):
    return {a.name: a.type for a in uml_class.attributes}


def _ea11(body: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="windows-1252"?>'
        '<XMI xmi.version="1.1" xmlns:UML="omg.org/UML1.3"><XMI.content>'
        '<UML:Model name="M" xmi.id="m"><UML:Namespace.ownedElement>'
        f"{body}</UML:Namespace.ownedElement></UML:Model></XMI.content></XMI>"
    ).encode("cp1252")


def _cls(xid, name, attrs=""):
    return (
        f'<UML:Class name="{name}" xmi.id="{xid}">'
        f"<UML:Classifier.feature>{attrs}</UML:Classifier.feature></UML:Class>"
    )


def _attr(name, type_name):
    return (
        f'<UML:Attribute name="{name}"><UML:ModelElement.taggedValue>'
        f'<UML:TaggedValue tag="type" value="{type_name}"/></UML:ModelElement.taggedValue></UML:Attribute>'
    )


def _assoc(ends, name="r"):
    body = "".join(
        f'<UML:AssociationEnd multiplicity="{m}" aggregation="{agg}" type="{t}"/>'
        for t, m, agg in ends
    )
    return (
        f'<UML:Association name="{name}"><UML:Association.connection>{body}'
        "</UML:Association.connection></UML:Association>"
    )


class TestRealEaSample:
    def test_imports_the_two_classes_attributes_association_and_layout(self):
        result = import_xmi((FIXTURES / "ea-basico.xml").read_bytes())
        model = result.model

        assert sorted(c.name for c in model.classes) == ["Class A", "Class B"]
        class_a, class_b = _by_name(model, "Class A"), _by_name(model, "Class B")
        assert _attrs(class_a) == {
            "Edad": PrimitiveType.INTEGER,
            "ID": PrimitiveType.INTEGER,
            "Name": PrimitiveType.STRING,
        }
        assert _attrs(class_b) == {"Id": PrimitiveType.INTEGER, "Name": PrimitiveType.STRING}

        (relationship,) = model.relationships
        assert relationship.kind is RelationshipKind.ASSOCIATION
        assert relationship.name == "Name A"
        assert relationship.source.class_id == class_a.id
        assert relationship.target.class_id == class_b.id
        assert relationship.source.multiplicity == Multiplicity(0, None)
        assert relationship.target.multiplicity == Multiplicity(0, None)

        # Cytoscape positions are node centers: EA box Left=100;Top=100;Right=217;Bottom=171.
        assert result.layout.positions[class_a.id].x == pytest.approx(158.5)
        assert result.layout.positions[class_a.id].y == pytest.approx(135.5)
        assert result.name == "Basic Class Diagram with Multiplicities"

    def test_ea_plumbing_is_not_reported_as_ignored_content(self):
        # EARootClass / DataType / Diagram are EA plumbing, not user content.
        warnings = import_xmi((FIXTURES / "ea-basico.xml").read_bytes()).warnings
        assert not [w for w in warnings if "EARootClass" in w or "DataType" in w]


class TestEaConstructs:
    def test_generalization_aggregation_and_composition_directions(self):
        body = (
            _cls("A", "Animal", _attr("n", "String"))
            + _cls("D", "Dog", _attr("m", "String"))
            + _cls("H", "House", _attr("n", "String"))
            + _cls("R", "Room", _attr("n", "String"))
            + '<UML:Generalization xmi.id="g" subtype="D" supertype="A"/>'
            + _assoc([("H", "1", "composite"), ("R", "1..*", "none")], name="has")
            + _assoc([("R", "0..1", "none"), ("A", "0..*", "shared")], name="holds")
        )
        model = import_xmi(_ea11(body)).model
        ids = {c.name: c.id for c in model.classes}
        kinds = {(r.kind, r.source.class_id, r.target.class_id) for r in model.relationships}

        assert (RelationshipKind.GENERALIZATION, ids["Dog"], ids["Animal"]) in kinds  # child -> parent
        assert (RelationshipKind.COMPOSITION, ids["House"], ids["Room"]) in kinds  # whole -> part
        # The diamond is on the SECOND end: ends are swapped so the whole is the source.
        aggregation = next(r for r in model.relationships if r.kind is RelationshipKind.AGGREGATION)
        assert aggregation.source.class_id == ids["Animal"]
        assert aggregation.source.multiplicity == Multiplicity(0, None)
        assert aggregation.target.multiplicity == Multiplicity(0, 1)

    def test_enumeration_typed_attribute_and_unknown_types(self):
        body = (
            '<UML:Enumeration name="Color" xmi.id="E"><UML:Enumeration.literal>'
            '<UML:EnumerationLiteral name="RED"/><UML:EnumerationLiteral name="BLUE"/>'
            "</UML:Enumeration.literal></UML:Enumeration>"
            + _cls("C", "Car", _attr("color", "Color") + _attr("blob", "Geometry") + _attr("km", "double"))
        )
        result = import_xmi(_ea11(body))
        car = _by_name(result.model, "Car")
        (enumeration,) = result.model.enumerations

        assert [lit.name for lit in enumeration.literals] == ["RED", "BLUE"]
        assert _attrs(car) == {
            "color": EnumerationRef(enumeration.id),
            "blob": PrimitiveType.STRING,  # unknown type falls back to String...
            "km": PrimitiveType.DECIMAL,
        }
        assert any("Geometry" in w for w in result.warnings)  # ...and says so

    def test_unsupported_elements_are_skipped_with_warnings_not_failures(self):
        body = (
            _cls("A", "Order", _attr("n", "String"))
            + '<UML:Actor name="Clerk" xmi.id="X"/>'
            + '<UML:Dependency name="uses" xmi.id="Y"/>'
            + _assoc([("A", "1", "none"), ("MISSING", "1", "none")], name="dangling")
        )
        result = import_xmi(_ea11(body))

        assert [c.name for c in result.model.classes] == ["Order"]
        assert result.model.relationships == ()
        joined = "\n".join(result.warnings)
        assert "Actor" in joined and "Dependency" in joined and "dangling" in joined


class TestXmi21:
    def test_basic_import_of_a_synthetic_xmi21_document(self):
        result = import_xmi((FIXTURES / "synthetic-xmi21.xml").read_bytes())
        model = result.model
        order, line, special = (_by_name(model, n) for n in ("Order", "OrderLine", "SpecialOrder"))
        (status,) = model.enumerations

        assert _attrs(order) == {"total": PrimitiveType.DECIMAL, "status": EnumerationRef(status.id)}
        assert _attrs(line) == {"qty": PrimitiveType.INTEGER}
        kinds = {r.kind: r for r in model.relationships}
        composition = kinds[RelationshipKind.COMPOSITION]
        # UML 2: the composite property sits on the PART end; the whole is the other end.
        assert composition.source.class_id == order.id and composition.target.class_id == line.id
        assert composition.target.multiplicity == Multiplicity(0, None)
        assert composition.source.multiplicity == Multiplicity(1, 1)
        generalization = kinds[RelationshipKind.GENERALIZATION]
        assert generalization.source.class_id == special.id
        assert generalization.target.class_id == order.id
        assert any("Actor" in w for w in result.warnings)


class TestFailures:
    @pytest.mark.parametrize(
        "payload, error",
        [
            (b"this is not xml at all", InvalidXmiError),
            (b"<a><b></a>", InvalidXmiError),
            (b"", InvalidXmiError),
            (b"<html><body>hi</body></html>", UnsupportedXmiError),
            (_ea11(""), UnsupportedXmiError),  # valid XMI, no classes
        ],
    )
    def test_rejects_unusable_input(self, payload, error):
        with pytest.raises(error):
            import_xmi(payload)

    def test_rejects_xxe_and_entity_expansion(self):
        xxe = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><XMI>&e;</XMI>'
        bomb = (
            b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]>'
            b"<XMI>&b;&b;</XMI>"
        )
        for payload in (xxe, bomb):
            with pytest.raises(InvalidXmiError):
                import_xmi(payload)

    def test_rejects_oversized_input(self):
        with pytest.raises(InvalidXmiError, match="5 MB"):
            import_xmi(b"<x/>" + b" " * MAX_XMI_BYTES)
