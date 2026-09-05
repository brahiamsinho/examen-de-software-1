"""RED: apps.uml_modeling.documents does not exist yet."""
import ast
import datetime
import uuid
from pathlib import Path

import pytest

from apps.uml_modeling.documents import DiagramLayout, Position, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import UmlAttribute, UmlClass
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import PrimitiveType

NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def _a_document(**overrides) -> ProjectDocument:
    defaults = dict(
        id=uuid.uuid4(),
        metadata=ProjectMetadata(name="My Project"),
        owner_id="42",
        model=CanonicalUmlModel(),
        layout=DiagramLayout(),
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return ProjectDocument(**defaults)


def test_new_document_receives_a_valid_unique_uuid():
    first = _a_document(id=uuid.uuid4())
    second = _a_document(id=uuid.uuid4())

    assert isinstance(first.id, uuid.UUID)
    assert first.id != second.id


def test_empty_owner_id_is_rejected():
    with pytest.raises(ValueError):
        _a_document(owner_id="")


def test_owner_id_round_trips_unchanged():
    document = _a_document(owner_id="42")

    assert document.owner_id == "42"


def test_no_django_auth_import_anywhere_in_the_package():
    package_root = Path(__file__).resolve().parent.parent

    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module] if node.module else []
            else:
                continue
            for name in names:
                assert name is None or "django.contrib.auth" not in name, (
                    f"{path} imports django.contrib.auth"
                )


LATER = datetime.datetime(2026, 1, 2, tzinfo=datetime.timezone.utc)


def test_moving_a_layout_position_leaves_the_uml_model_unchanged():
    order_class = UmlClass(id=new_id(), name="Order")
    document = _a_document(model=CanonicalUmlModel(classes=(order_class,)))

    moved = document.with_layout(
        DiagramLayout(positions={order_class.id: Position(10, 20)}), now=LATER
    )

    assert moved.model == document.model
    assert moved.model.classes == (order_class,)


def test_adding_an_attribute_leaves_the_layout_unaffected():
    order_class = UmlClass(id=new_id(), name="Order")
    layout = DiagramLayout(positions={order_class.id: Position(10, 20)})
    document = _a_document(model=CanonicalUmlModel(classes=(order_class,)), layout=layout)

    attribute = UmlAttribute(id=new_id(), name="total", type=PrimitiveType.DECIMAL)
    updated_class = UmlClass(id=order_class.id, name="Order", attributes=(attribute,))
    updated = document.with_model(CanonicalUmlModel(classes=(updated_class,)), now=LATER)

    assert updated.layout == layout


def test_with_model_increments_revision_by_exactly_one():
    document = _a_document()

    updated = document.with_model(document.model, now=LATER)

    assert updated.revision == document.revision + 1
    assert updated.updated_at == LATER


def test_with_layout_increments_revision_by_exactly_one():
    document = _a_document()

    updated = document.with_layout(document.layout, now=LATER)

    assert updated.revision == document.revision + 1
    assert updated.updated_at == LATER


def test_two_independent_copies_mutating_concurrently_raise_nothing():
    document = _a_document()

    first_copy = document.with_model(document.model, now=LATER)
    second_copy = document.with_layout(document.layout, now=LATER)

    assert first_copy.revision == document.revision + 1
    assert second_copy.revision == document.revision + 1
