"""`SetClassAbstract`: marks a class abstract, or concrete again."""
import datetime

from apps.uml_commands.commands import SetClassAbstract
from apps.uml_commands.dispatcher import apply
from apps.uml_commands.handlers.classes import set_class_abstract
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel

from ..factories import a_class, a_document

NOW = datetime.datetime(2026, 1, 2, tzinfo=datetime.timezone.utc)


def test_it_marks_the_class_abstract_and_leaves_the_others_alone():
    shape, order = a_class(name="Shape"), a_class(name="Order")
    model = CanonicalUmlModel(classes=(shape, order))

    result = set_class_abstract(model, SetClassAbstract(class_id=shape.id, is_abstract=True))

    assert result.class_by_id(shape.id).is_abstract is True
    assert result.class_by_id(order.id).is_abstract is False
    assert result.class_by_id(shape.id).name == "Shape"


def test_it_makes_an_abstract_class_concrete_again():
    shape = a_class(name="Shape")
    abstract = set_class_abstract(CanonicalUmlModel(classes=(shape,)), SetClassAbstract(class_id=shape.id, is_abstract=True))

    result = set_class_abstract(abstract, SetClassAbstract(class_id=shape.id, is_abstract=False))

    assert result.class_by_id(shape.id).is_abstract is False


def test_an_unknown_class_leaves_the_model_unchanged():
    model = CanonicalUmlModel(classes=(a_class(name="Shape"),))

    assert set_class_abstract(model, SetClassAbstract(class_id=new_id(), is_abstract=True)) is model


def test_the_dispatcher_runs_it_like_any_other_command():
    shape = a_class(name="Shape")
    document = a_document(model=CanonicalUmlModel(classes=(shape,)))

    result = apply(document, SetClassAbstract(class_id=shape.id, is_abstract=True), now=NOW)

    assert result.document.model.class_by_id(shape.id).is_abstract is True
    assert result.document.revision == document.revision + 1
