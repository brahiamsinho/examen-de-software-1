"""The log says which class was made abstract."""
from apps.session_log import services as log
from apps.uml_commands.commands import SetClassAbstract
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.tests.factories import a_class


def test_marking_a_class_abstract_is_logged_with_the_class_name():
    shape = a_class(name="Shape")

    described = log.describe_commands([SetClassAbstract(class_id=shape.id, is_abstract=True)], CanonicalUmlModel(classes=(shape,)))

    assert described == [{"type": "SetClassAbstract", "label": "Shape"}]
