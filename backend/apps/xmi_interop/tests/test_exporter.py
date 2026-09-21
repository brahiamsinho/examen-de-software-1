"""Exporter output shape and the import -> export -> import round trip."""
import datetime
import pathlib
import uuid
from xml.etree.ElementTree import fromstring

from apps.uml_modeling.documents import DiagramLayout, Position, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import (
    Enumeration,
    EnumerationLiteral,
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlClass,
    UmlOperation,
)
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity, PrimitiveType
from apps.xmi_interop.exporter import export_xmi
from apps.xmi_interop.importer import import_xmi

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "ea-basico.xml"
NOW = datetime.datetime(2026, 9, 20, 12, 0, tzinfo=datetime.timezone.utc)


def _document(model, layout=None, name="Demo") -> ProjectDocument:
    return ProjectDocument(
        id=uuid.uuid4(),
        metadata=ProjectMetadata(name=name),
        owner_id="u1",
        model=model,
        layout=layout or DiagramLayout(),
        created_at=NOW,
        updated_at=NOW,
    )


def _signature(model, layout=None):
    """Id-free structural summary, so two imports (fresh ids each time) can be compared."""
    names = {c.id: c.name for c in model.classes}
    enum_names = {e.id: e.name for e in model.enumerations}

    def type_name(t):
        return enum_names[t.enumeration_id] if isinstance(t, EnumerationRef) else t.value

    return {
        "classes": sorted(
            (c.name, tuple((a.name, type_name(a.type), a.visibility) for a in c.attributes),
             tuple(o.name for o in c.operations))
            for c in model.classes
        ),
        "enums": sorted((e.name, tuple(lit.name for lit in e.literals)) for e in model.enumerations),
        "relationships": sorted(
            (r.kind.value, names[r.source.class_id], r.source.multiplicity.lower, r.source.multiplicity.upper,
             names[r.target.class_id], r.target.multiplicity.lower, r.target.multiplicity.upper, r.name or "")
            for r in model.relationships
        ),
        "positions": sorted(
            (names[cid], p.x, p.y) for cid, p in (layout.positions if layout else {}).items()
        ),
    }


def _rich_model():
    order = UmlClass("c1", "Órdenes de compra", (
        UmlAttribute("a1", "total", PrimitiveType.DECIMAL),
        UmlAttribute("a2", "state", EnumerationRef("e1")),
        UmlAttribute("a3", "note", PrimitiveType.TEXT),
    ), (UmlOperation("o1", "close"),))
    line = UmlClass("c2", "Line", (UmlAttribute("a4", "qty", PrimitiveType.LONG),))
    special = UmlClass("c3", "Special <&> \U0001f600", (UmlAttribute("a5", "flag", PrimitiveType.BOOLEAN),))
    one, many = Multiplicity(1, 1), Multiplicity(0, None)
    return CanonicalUmlModel(
        classes=(order, line, special),
        enumerations=(Enumeration("e1", "State", (EnumerationLiteral("l1", "OPEN"), EnumerationLiteral("l2", "DONE"))),),
        relationships=(
            Relationship("r1", RelationshipKind.COMPOSITION, RelationshipEnd("c1", one, "order"),
                         RelationshipEnd("c2", many, "lines"), "contains"),
            Relationship("r2", RelationshipKind.AGGREGATION, RelationshipEnd("c1", many), RelationshipEnd("c3", Multiplicity(0, 1))),
            Relationship("r3", RelationshipKind.GENERALIZATION, RelationshipEnd("c3", one), RelationshipEnd("c1", one)),
        ),
    )


class TestExportShape:
    def test_matches_the_ea_dialect_and_carries_layout(self):
        model = _rich_model()
        layout = DiagramLayout({"c1": Position(158.5, 135.5)})
        data = export_xmi(_document(model, layout, name="My Diagram"))
        root = fromstring(data)

        assert data.startswith(b"<?xml version='1.0' encoding='windows-1252'?>")
        assert root.tag == "XMI" and root.get("xmi.version") == "1.1"
        text = data.decode("cp1252")
        assert "xmlns:UML=\"omg.org/UML1.3\"" in text
        assert 'geometry="Left=100;Top=100;Right=217;Bottom=171;"' in text
        assert 'diagramType="ClassDiagram"' in text and 'name="My Diagram"' in text
        assert 'aggregation="composite"' in text and 'aggregation="shared"' in text
        assert "subtype=" in text and "supertype=" in text

    def test_export_is_deterministic(self):
        document = _document(_rich_model())
        assert export_xmi(document) == export_xmi(document)


class TestRoundTrip:
    def test_real_ea_sample_survives_import_export_import(self):
        first = import_xmi(FIXTURE.read_bytes())
        exported = export_xmi(_document(first.model, first.layout, name=first.name))
        second = import_xmi(exported)

        assert _signature(second.model, second.layout) == _signature(first.model, first.layout)
        assert second.name == first.name
        assert [w for w in second.warnings if not w.startswith("Validación")] == []

    def test_rich_model_round_trips_enums_kinds_roles_and_special_characters(self):
        model = _rich_model()
        second = import_xmi(export_xmi(_document(model)))

        assert _signature(second.model) == _signature(model)
        roles = {r.name: (r.source.role, r.target.role) for r in second.model.relationships}
        assert roles["contains"] == ("order", "lines")
