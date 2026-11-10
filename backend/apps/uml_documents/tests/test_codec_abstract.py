"""`is_abstract` is saved with the diagram, and diagrams saved before it existed still open."""
from apps.uml_documents import codec
from apps.uml_documents.tests.factories import a_metadata
from apps.uml_modeling.documents import DiagramLayout
from apps.uml_modeling.domain.elements import UmlClass
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel


def _model(*, abstract: bool) -> CanonicalUmlModel:
    return CanonicalUmlModel(classes=(UmlClass(id=new_id(), name="Shape", is_abstract=abstract),))


def test_an_abstract_class_round_trips():
    model = _model(abstract=True)

    data = codec.to_json(a_metadata(), model, DiagramLayout())
    _, decoded, _ = codec.from_json(data)

    assert data["model"]["classes"][0]["is_abstract"] is True
    assert decoded == model


def test_a_concrete_class_is_saved_as_not_abstract():
    data = codec.to_json(a_metadata(), _model(abstract=False), DiagramLayout())

    assert data["model"]["classes"][0]["is_abstract"] is False


def test_a_diagram_saved_before_the_flag_existed_opens_with_concrete_classes():
    data = codec.to_json(a_metadata(), _model(abstract=False), DiagramLayout())
    del data["model"]["classes"][0]["is_abstract"]  # what an old stored diagram looks like

    _, decoded, _ = codec.from_json(data)

    assert decoded.classes[0].is_abstract is False
