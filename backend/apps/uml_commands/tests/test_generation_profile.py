"""`SetGenerationProfile` handler and the shared metadata-pruning primitive
(design.md DD156, DD158): the handler owns exactly the `"profile"` key of one
`generation_metadata` entry and never raises (DD6).
"""
import copy

import pytest

from apps.uml_modeling.domain.elements import RelationshipKind, UmlAttribute, UmlOperation
from apps.uml_modeling.domain.ids import ElementId, new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import PrimitiveType
from apps.uml_commands.commands import (
    RemoveAttribute,
    RemoveClass,
    RemoveOperation,
    RemoveRelationship,
    SetGenerationProfile,
)
from apps.uml_commands.handlers.attributes import remove_attribute
from apps.uml_commands.handlers.classes import remove_class
from apps.uml_commands.handlers.generation_profile import (
    prune_generation_metadata,
    set_generation_profile,
)
from apps.uml_commands.handlers.operations import remove_operation
from apps.uml_commands.handlers.relationships import remove_relationship

from .factories import a_class, a_relationship, a_relationship_end

_ATTRIBUTE = UmlAttribute(id=ElementId("attr-1"), name="reference", type=PrimitiveType.STRING)
_CLASS = a_class(id=ElementId("cls-1"), name="Order", attributes=(_ATTRIBUTE,))
_PROFILE = {"entity": True, "crud": ["create", "read"]}


def _model(metadata: dict) -> CanonicalUmlModel:
    return CanonicalUmlModel(classes=(_CLASS,), generation_metadata=metadata)


@pytest.mark.parametrize(
    ("initial", "element_id", "profile", "expected"),
    [
        pytest.param({}, "cls-1", _PROFILE, {"cls-1": {"profile": _PROFILE}}, id="set-on-class"),
        pytest.param(
            {}, "attr-1", {"searchable": True}, {"attr-1": {"profile": {"searchable": True}}},
            id="set-on-attribute",
        ),
        pytest.param(
            {"cls-1": {"source": "voice", "confidence": 0.9}},
            "cls-1",
            _PROFILE,
            {"cls-1": {"source": "voice", "confidence": 0.9, "profile": _PROFILE}},
            id="set-preserves-sibling-keys",
        ),
        pytest.param(
            {"cls-1": {"source": "voice", "profile": {"entity": False, "auditable": True}}},
            "cls-1",
            {"readOnly": True},
            {"cls-1": {"source": "voice", "profile": {"readOnly": True}}},
            id="set-replaces-the-whole-profile-not-merge",
        ),
        pytest.param(
            {"cls-1": {"source": "voice", "profile": _PROFILE}},
            "cls-1",
            None,
            {"cls-1": {"source": "voice"}},
            id="none-removes-only-profile",
        ),
        pytest.param(
            {"cls-1": {"source": "voice", "profile": _PROFILE}},
            "cls-1",
            {},
            {"cls-1": {"source": "voice"}},
            id="empty-mapping-removes-only-profile",
        ),
        pytest.param(
            {"cls-1": {"profile": _PROFILE}, "other": {"source": "x"}},
            "cls-1",
            None,
            {"other": {"source": "x"}},
            id="clear-prunes-the-entry-when-it-becomes-empty",
        ),
        pytest.param(
            {"cls-1": {"source": "voice"}},
            "cls-1",
            None,
            {"cls-1": {"source": "voice"}},
            id="clear-on-a-sibling-only-entry-keeps-it",
        ),
    ],
)
def test_set_generation_profile_table(initial, element_id, profile, expected):
    model = _model(initial)

    result = set_generation_profile(
        model, SetGenerationProfile(element_id=ElementId(element_id), profile=profile)
    )

    assert result.generation_metadata == expected


def test_set_generation_profile_does_not_touch_classes_or_relationships():
    model = _model({})

    result = set_generation_profile(
        model, SetGenerationProfile(element_id=ElementId("cls-1"), profile=_PROFILE)
    )

    assert result.classes == model.classes
    assert result.enumerations == model.enumerations
    assert result.relationships == model.relationships


@pytest.mark.parametrize("profile", [_PROFILE, None, {}])
def test_unknown_element_id_returns_the_model_unchanged_and_does_not_raise(profile):
    model = _model({"cls-1": {"source": "voice"}})

    result = set_generation_profile(
        model, SetGenerationProfile(element_id=new_id(), profile=profile)
    )

    assert result is model


def test_clearing_an_absent_profile_returns_the_same_model():
    model = _model({})

    result = set_generation_profile(model, SetGenerationProfile(element_id=ElementId("cls-1")))

    assert result is model


def test_set_generation_profile_never_mutates_the_input_model():
    initial = {"cls-1": {"source": "voice", "profile": {"entity": False}}}
    model = _model(copy.deepcopy(initial))

    set_generation_profile(
        model, SetGenerationProfile(element_id=ElementId("cls-1"), profile=_PROFILE)
    )
    set_generation_profile(model, SetGenerationProfile(element_id=ElementId("cls-1"), profile=None))

    assert model.generation_metadata == initial


# --- prune_generation_metadata: the shared cascade primitive (DD158) -------


def _sort(attribute_id: str) -> dict:
    return {"profile": {"entity": True, "defaultSort": {"attribute": attribute_id, "direction": "asc"}}}


def test_prune_drops_entries_keyed_by_removed_ids():
    metadata = {"gone": {"profile": {"entity": True}}, "kept": {"source": "voice"}}

    result = prune_generation_metadata(metadata, frozenset({ElementId("gone")}))

    assert result == {"kept": {"source": "voice"}}


def test_prune_clears_a_foreign_default_sort_pointing_at_a_removed_id():
    metadata = {"root": _sort("child-attr")}

    result = prune_generation_metadata(metadata, frozenset({ElementId("child-attr")}))

    assert result == {"root": {"profile": {"entity": True}}}


def test_prune_drops_profile_when_default_sort_was_its_only_key():
    metadata = {"root": {"source": "voice", "profile": {"defaultSort": {"attribute": "a", "direction": "asc"}}}}

    result = prune_generation_metadata(metadata, frozenset({ElementId("a")}))

    assert result == {"root": {"source": "voice"}}


def test_prune_drops_the_entry_when_profile_was_its_only_key():
    metadata = {"root": {"profile": {"defaultSort": {"attribute": "a", "direction": "asc"}}}}

    result = prune_generation_metadata(metadata, frozenset({ElementId("a")}))

    assert result == {}


def test_prune_leaves_non_mapping_shapes_untouched_and_never_raises():
    metadata = {
        "not-a-mapping": "text",
        "profile-not-a-mapping": {"profile": ["x"]},
        "sort-not-a-mapping": {"profile": {"defaultSort": "a"}},
        "attribute-not-a-string": {"profile": {"defaultSort": {"attribute": 7}}},
    }

    result = prune_generation_metadata(metadata, frozenset({ElementId("a")}))

    assert result is metadata


def test_prune_returns_the_same_object_when_nothing_changed():
    metadata = {"kept": _sort("other"), "plain": {"source": "voice"}}

    assert prune_generation_metadata(metadata, frozenset({ElementId("gone")})) is metadata
    assert prune_generation_metadata({}, frozenset({ElementId("gone")})) == {}


# --- RemoveClass / RemoveAttribute cascade (DD158) --------------------------


def _hierarchy_model(metadata: dict) -> CanonicalUmlModel:
    root_attr = UmlAttribute(id=ElementId("root-attr"), name="code", type=PrimitiveType.STRING)
    child_attr = UmlAttribute(id=ElementId("child-attr"), name="extra", type=PrimitiveType.STRING)
    operation = UmlOperation(id=ElementId("op-1"), name="ship")
    root = a_class(id=ElementId("root"), name="Vehicle", attributes=(root_attr,), operations=(operation,))
    child = a_class(id=ElementId("child"), name="Car", attributes=(child_attr,))
    generalization = a_relationship(
        id=ElementId("gen-1"),
        kind=RelationshipKind.GENERALIZATION,
        source=a_relationship_end(class_id=child.id),
        target=a_relationship_end(class_id=root.id),
    )
    return CanonicalUmlModel(
        classes=(root, child), relationships=(generalization,), generation_metadata=metadata
    )


def test_remove_class_drops_the_class_entry_and_each_attribute_entry():
    model = _hierarchy_model(
        {
            "child": {"profile": {"entity": True}},
            "child-attr": {"profile": {"searchable": True}},
            "root-attr": {"profile": {"sortable": True}},
        }
    )

    result = remove_class(model, RemoveClass(class_id=ElementId("child")))

    assert result.generation_metadata == {"root-attr": {"profile": {"sortable": True}}}


def test_remove_class_clears_a_foreign_root_default_sort_on_a_removed_descendant_attribute():
    model = _hierarchy_model({"root": _sort("child-attr"), "child-attr": {"profile": {"sortable": True}}})

    result = remove_class(model, RemoveClass(class_id=ElementId("child")))

    assert result.generation_metadata == {"root": {"profile": {"entity": True}}}


def test_remove_attribute_drops_the_attribute_entry_and_clears_default_sort_pointing_at_it():
    model = _hierarchy_model({"root": _sort("root-attr"), "root-attr": {"profile": {"sortable": True}}})

    result = remove_attribute(
        model, RemoveAttribute(class_id=ElementId("root"), attribute_id=ElementId("root-attr"))
    )

    assert result.generation_metadata == {"root": {"profile": {"entity": True}}}


def test_remove_attribute_clears_a_foreign_root_default_sort_on_a_descendant_attribute():
    model = _hierarchy_model({"root": _sort("child-attr")})

    result = remove_attribute(
        model, RemoveAttribute(class_id=ElementId("child"), attribute_id=ElementId("child-attr"))
    )

    assert result.generation_metadata == {"root": {"profile": {"entity": True}}}


def test_remove_class_and_attribute_leave_unrelated_entries_untouched():
    unrelated = {"root": _sort("root-attr"), "elsewhere": {"source": "voice"}}
    model = _hierarchy_model(unrelated)

    after_class = remove_class(model, RemoveClass(class_id=ElementId("child")))
    after_attribute = remove_attribute(
        model, RemoveAttribute(class_id=ElementId("child"), attribute_id=ElementId("child-attr"))
    )

    assert after_class.generation_metadata == unrelated
    assert after_attribute.generation_metadata == unrelated


def test_remove_class_and_attribute_keep_the_same_metadata_object_when_nothing_prunes():
    model = _hierarchy_model({})

    after_class = remove_class(model, RemoveClass(class_id=ElementId("child")))
    after_attribute = remove_attribute(
        model, RemoveAttribute(class_id=ElementId("child"), attribute_id=ElementId("child-attr"))
    )

    assert after_class.generation_metadata is model.generation_metadata
    assert after_attribute.generation_metadata is model.generation_metadata


def test_relationship_and_operation_keyed_entries_are_kept_on_removal():
    metadata = {"gen-1": {"source": "voice"}, "op-1": {"source": "voice"}}
    model = _hierarchy_model(metadata)

    after_relationship = remove_relationship(
        model, RemoveRelationship(relationship_id=ElementId("gen-1"))
    )
    after_operation = remove_operation(
        model, RemoveOperation(class_id=ElementId("root"), operation_id=ElementId("op-1"))
    )
    after_class = remove_class(model, RemoveClass(class_id=ElementId("root")))

    assert after_relationship.generation_metadata == metadata
    assert after_operation.generation_metadata == metadata
    assert after_class.generation_metadata == metadata
