"""A dependency says "uses", not "stores": it must never become a foreign key or a join table."""
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.uml_commands.tests.factories import a_class, a_relationship, a_relationship_end
from apps.uml_modeling.domain.elements import RelationshipKind, UmlAttribute
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity, PrimitiveType


def _class(name: str):
    return a_class(name=name, attributes=(UmlAttribute(id=new_id(), name="nombre", type=PrimitiveType.STRING),))


def _dependency(client, supplier, *, many: bool = False):
    multiplicity = Multiplicity(0, None) if many else Multiplicity(1, 1)
    return a_relationship(
        kind=RelationshipKind.DEPENDENCY,
        source=a_relationship_end(class_id=client.id, multiplicity=multiplicity),
        target=a_relationship_end(class_id=supplier.id, multiplicity=multiplicity),
    )


def test_a_dependency_adds_no_column_and_no_table():
    pedido, calculadora = _class("Pedido"), _class("Calculadora")
    plain = CanonicalUmlModel(classes=(pedido, calculadora))
    with_dependency = CanonicalUmlModel(classes=(pedido, calculadora), relationships=(_dependency(pedido, calculadora),))

    assert map_to_relational(with_dependency) == map_to_relational(plain)


def test_even_a_many_to_many_looking_dependency_does_not_make_a_join_table():
    pedido, producto = _class("Pedido"), _class("Producto")
    plain = CanonicalUmlModel(classes=(pedido, producto))
    with_dependency = CanonicalUmlModel(
        classes=(pedido, producto), relationships=(_dependency(pedido, producto, many=True),)
    )

    assert map_to_relational(with_dependency) == map_to_relational(plain)
