"""Exporter output shape and the import -> export -> import round trip."""
import datetime
import pathlib
import re
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
from apps.xmi_interop.exporter import _ea_id, export_xmi
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


def _local(tag: str) -> str:
    """Strip the `{omg.org/UML1.3}` namespace ElementTree resolves `UML:`
    tags into (the `xmlns:UML` attribute on the root IS a real namespace
    declaration, so `el.tag` is never the literal `"UML:Class"` string)."""
    return tag.rsplit("}", 1)[-1]


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
        # c1 ("Órdenes de compra") has 3 attributes + 1 operation, so its box
        # grows past the 71px floor to fit all four feature rows (DD172).
        assert 'geometry="Left=100;Top=88;Right=217;Bottom=184;"' in text
        assert 'diagramType="ClassDiagram"' in text and 'name="My Diagram"' in text
        assert 'aggregation="composite"' in text and 'aggregation="shared"' in text
        assert "subtype=" in text and "supertype=" in text

    def test_export_is_deterministic(self):
        document = _document(_rich_model())
        assert export_xmi(document) == export_xmi(document)

    def test_box_height_grows_with_feature_count_but_never_shrinks_below_the_floor(self):
        # A class with no attributes/operations keeps the original fixed
        # height (DD172); c2 ("Line") has a single attribute, still under the
        # floor. c1 has 4 feature rows and must be taller than both.
        model = _rich_model()
        text = export_xmi(_document(model)).decode("cp1252")

        def bottom_minus_top(class_id: str) -> int:
            xid = _ea_id("EAID", class_id)
            match = re.search(rf'geometry="Left=\d+;Top=(\d+);Right=\d+;Bottom=(\d+);" subject="{xid}"', text)
            top, bottom = int(match.group(1)), int(match.group(2))
            return bottom - top

        assert bottom_minus_top("c2") == 71  # 1 feature row: floor applies
        assert bottom_minus_top("c1") > 71  # 4 feature rows: grows past the floor


class TestRoundTrip:
    def test_real_ea_sample_survives_import_export_import(self):
        first = import_xmi(FIXTURE.read_bytes())
        exported = export_xmi(_document(first.model, first.layout, name=first.name))
        second = import_xmi(exported)

        first_signature, second_signature = _signature(first.model, first.layout), _signature(second.model, second.layout)
        # ea-basico.xml's single association ("Name A") is many-to-many on
        # BOTH ends (0..*/0..*), so exporting it now attaches a real
        # Enterprise Architect "Association Class" to it (design.md DD185):
        # the association itself is written completely normally -- same
        # kind, endpoints, multiplicities, and NAME as any other -- with an
        # extra `associationclass`/`subtype` tag pair, plus a separate
        # empty class carrying the reverse `conID` tag. Re-importing hides
        # that empty class (`importer._hide_association_classes`) and
        # leaves the association untouched, so THIS round trip is now
        # byte-for-byte identical in every field, including the name --
        # unlike the earlier two-synthetic-associations design this
        # replaced, nothing about the relationship is lossy anymore.
        assert {**first_signature, "positions": None} == {**second_signature, "positions": None}
        # EA's geometry is integer pixels; centering an odd total (box
        # height + 2*top) over 2 can round either way, so only whole-pixel
        # fidelity is guaranteed, never sub-pixel (DD172).
        for (name, x, y), (name2, x2, y2) in zip(
            sorted(first_signature["positions"]), sorted(second_signature["positions"])
        ):
            assert name == name2
            assert abs(x - x2) <= 1 and abs(y - y2) <= 1
        assert second.name == first.name
        non_validation = [w for w in second.warnings if not w.startswith("Validación")]
        assert len(non_validation) == 1 and "clase de asociación" in non_validation[0]

    def test_rich_model_round_trips_enums_kinds_roles_and_special_characters(self):
        model = _rich_model()
        second = import_xmi(export_xmi(_document(model)))

        assert _signature(second.model) == _signature(model)
        roles = {r.name: (r.source.role, r.target.role) for r in second.model.relationships}
        assert roles["contains"] == ("order", "lines")


def _tagged(el):
    holder = next((c for c in el if _local(c.tag) == "ModelElement.taggedValue"), None)
    if holder is None:
        return {}
    return {t.get("tag"): t.get("value") for t in holder}


class TestJoinTableExport:
    """A both-ends-many relationship (mapper.py's `source_many and
    target_many` join-table condition) gets a real Enterprise Architect
    "Association Class" attached to it (design.md DD185, format verified
    from a real EA export): the association itself is written completely
    normally -- one element, its real multiplicities, its real name --
    plus an `associationclass`/`subtype` tag pair pointing at a separate,
    empty class, which itself carries the reverse `conID` tag. This is
    what makes EA draw the join table as its own box, dashed-line-attached
    to the *..* association, instead of a bare line."""

    def _student_course_model(self):
        student = UmlClass("c1", "Student", (UmlAttribute("a1", "name", PrimitiveType.STRING),))
        course = UmlClass("c2", "Course", (UmlAttribute("a2", "title", PrimitiveType.STRING),))
        many = Multiplicity(0, None)
        return CanonicalUmlModel(
            classes=(student, course),
            relationships=(
                Relationship(
                    "r1", RelationshipKind.ASSOCIATION,
                    RelationshipEnd("c1", many), RelationshipEnd("c2", many), "enrolled_in",
                ),
            ),
        )

    def test_both_ends_many_association_gets_an_attached_association_class(self):
        data = export_xmi(_document(self._student_course_model()))
        root = fromstring(data)

        classes = [c for c in root.iter() if _local(c.tag) == "Class"]
        class_names = [c.get("name") for c in classes]
        assert "Student_Course" in class_names
        # The real classes are untouched -- no direct Student<->Course
        # association was replaced by anything.
        assert "Student" in class_names and "Course" in class_names

        join_class = next(c for c in classes if c.get("name") == "Student_Course")
        # DD186: the join class's attributes are the REAL relational
        # columns (id + the two FKs), computed via `map_to_relational` --
        # matching exactly what the canvas's own join-table preview hint
        # already shows, not left empty.
        features = next(c for c in join_class if _local(c.tag) == "Classifier.feature")
        attribute_names = [a.get("name") for a in features if _local(a.tag) == "Attribute"]
        assert attribute_names == ["id", "student_id", "course_id"]
        # And it's tagged as OUR OWN synthetic marker, so the importer can
        # still recognize/hide it now that it isn't empty anymore.
        assert _tagged(join_class).get("modelia_synthetic") == "join_table"

        # Exactly ONE association: the real Student<->Course relationship,
        # never a pair of synthetic many-to-one associations to the join class.
        associations = [a for a in root.iter() if _local(a.tag) == "Association"]
        assert len(associations) == 1
        assoc = associations[0]
        assert assoc.get("name") == "enrolled_in"  # the real name survives, unlike the earlier design

        connection = next(c for c in assoc if _local(c.tag) == "Association.connection")
        ends = [e for e in connection if _local(e.tag) == "AssociationEnd"]
        student_id, course_id = _ea_id("EAID", "c1"), _ea_id("EAID", "c2")
        assert {e.get("type") for e in ends} == {student_id, course_id}
        assert {e.get("multiplicity") for e in ends} == {"0..*"}

        assoc_tags = _tagged(assoc)
        assert assoc_tags.get("subtype") == "Class"
        assert assoc_tags.get("associationclass") == join_class.get("xmi.id")
        assert _tagged(join_class).get("conID") == assoc.get("xmi.id")

    def test_self_referencing_both_ends_many_association_keeps_one_association(self):
        employee = UmlClass("c1", "Employee")
        many = Multiplicity(0, None)
        model = CanonicalUmlModel(
            classes=(employee,),
            relationships=(
                Relationship(
                    "r1", RelationshipKind.ASSOCIATION,
                    RelationshipEnd("c1", many, "manager"), RelationshipEnd("c1", many, "report"),
                ),
            ),
        )
        data = export_xmi(_document(model))
        root = fromstring(data)

        class_names = [c.get("name") for c in root.iter() if _local(c.tag) == "Class"]
        assert "Employee_Employee" in class_names
        assert class_names.count("Employee") == 1  # the real class isn't duplicated

        # Self-referencing is now trivially correct: still just ONE
        # association (both ends pointing at Employee), so there is no
        # overlapping-edge rendering risk left to work around at all.
        associations = [a for a in root.iter() if _local(a.tag) == "Association"]
        assert len(associations) == 1
        connection = next(c for c in associations[0] if _local(c.tag) == "Association.connection")
        ends = [e for e in connection if _local(e.tag) == "AssociationEnd"]
        employee_id = _ea_id("EAID", "c1")
        assert {e.get("type") for e in ends} == {employee_id}

    def test_join_class_gets_its_own_diagram_position(self):
        model = self._student_course_model()
        layout = DiagramLayout({"c1": Position(100, 100), "c2": Position(300, 100)})
        data = export_xmi(_document(model, layout))
        root = fromstring(data)

        join_id = next(
            c.get("xmi.id") for c in root.iter() if _local(c.tag) == "Class" and c.get("name") == "Student_Course"
        )
        diagram_elements = [
            e for e in root.iter() if _local(e.tag) == "DiagramElement" and e.get("subject") == join_id
        ]
        assert len(diagram_elements) == 1
        assert "Left=" in diagram_elements[0].get("geometry", "")


class TestJoinTableRoundTrip:
    def test_both_ends_many_relationships_round_trip_through_the_join_class_pattern(self):
        student = UmlClass("c1", "Student", (UmlAttribute("a1", "name", PrimitiveType.STRING),))
        course = UmlClass("c2", "Course", (UmlAttribute("a2", "title", PrimitiveType.STRING),))
        employee = UmlClass("c3", "Employee", (UmlAttribute("a3", "name", PrimitiveType.STRING),))
        many = Multiplicity(0, None)
        model = CanonicalUmlModel(
            classes=(student, course, employee),
            relationships=(
                Relationship(
                    "r1", RelationshipKind.ASSOCIATION,
                    RelationshipEnd("c1", many), RelationshipEnd("c2", many), "enrolled_in",
                ),
                Relationship(
                    "r2", RelationshipKind.ASSOCIATION,
                    RelationshipEnd("c3", many, "manager"), RelationshipEnd("c3", many, "report"),
                ),
            ),
        )

        result = import_xmi(export_xmi(_document(model)))
        reimported = result.model

        assert sorted(c.name for c in reimported.classes) == ["Course", "Employee", "Student"]
        assert len(reimported.relationships) == 2
        names = {c.id: c.name for c in reimported.classes}
        pairs = {
            frozenset((names[r.source.class_id], names[r.target.class_id])) for r in reimported.relationships
        }
        assert pairs == {frozenset({"Student", "Course"}), frozenset({"Employee"})}
        for relationship in reimported.relationships:
            assert relationship.source.multiplicity == many
            assert relationship.target.multiplicity == many
        # Names now round-trip too (design.md DD185) -- the association
        # class approach never touches the association's own name field.
        assert {r.name for r in reimported.relationships} == {"enrolled_in", None}
        assert sum("clase de asociación" in w for w in result.warnings) == 2
