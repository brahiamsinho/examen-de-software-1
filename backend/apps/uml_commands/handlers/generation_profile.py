"""Handler for the generation-profile command (DD156).

`set_generation_profile` owns exactly the `"profile"` key of one
`generation_metadata[element_id]` entry; sibling keys are preserved
byte-for-byte. Like every handler it is a pure structural transform that
never raises: an id matching neither a class nor an attribute
short-circuits to the unchanged model (DD6). Semantic rules live in
`apps.uml_documents.services`, not here.
"""
import dataclasses
from collections.abc import Mapping

from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.commands import SetGenerationProfile


def set_generation_profile(
    model: CanonicalUmlModel, command: SetGenerationProfile
) -> CanonicalUmlModel:
    """Owns exactly the "profile" key of generation_metadata[element_id]."""
    element_id = command.element_id
    is_class = model.class_by_id(element_id) is not None
    is_attribute = any(
        attribute.id == element_id
        for uml_class in model.classes
        for attribute in uml_class.attributes
    )
    if not is_class and not is_attribute:
        return model

    metadata = dict(model.generation_metadata)
    entry = dict(metadata.get(element_id, {}))
    if command.profile:
        entry["profile"] = dict(command.profile)
    else:
        entry.pop("profile", None)

    if entry:
        metadata[element_id] = entry
    else:
        metadata.pop(element_id, None)

    if metadata == model.generation_metadata:
        return model
    return dataclasses.replace(model, generation_metadata=metadata)


def prune_generation_metadata(
    metadata: Mapping[ElementId, Mapping[str, object]],
    removed_ids: frozenset[ElementId],
) -> Mapping[ElementId, Mapping[str, object]]:
    """Cascade for `RemoveClass`/`RemoveAttribute` (DD158).

    Drops every entry keyed by a removed id, and clears `defaultSort` on
    any surviving entry whose `defaultSort.attribute` names a removed id
    (an inheritance root may sort by a descendant's attribute, DD157).
    Structural only: any non-`Mapping` shape is left untouched. Returns
    the same object when nothing changed so callers can skip `replace`.
    """
    pruned: dict[ElementId, Mapping[str, object]] = {}
    changed = False
    for key, entry in metadata.items():
        if key in removed_ids:
            changed = True
            continue
        updated = _without_dangling_default_sort(entry, removed_ids)
        if updated is entry:
            pruned[key] = entry
            continue
        changed = True
        if updated:
            pruned[key] = updated
    return pruned if changed else metadata


def _without_dangling_default_sort(
    entry: Mapping[str, object], removed_ids: frozenset[ElementId]
) -> Mapping[str, object]:
    """`entry` itself when untouched; otherwise a copy that may be empty."""
    if not isinstance(entry, Mapping):
        return entry
    profile = entry.get("profile")
    if not isinstance(profile, Mapping):
        return entry
    default_sort = profile.get("defaultSort")
    if not isinstance(default_sort, Mapping):
        return entry
    attribute = default_sort.get("attribute")
    if not isinstance(attribute, str) or ElementId(attribute) not in removed_ids:
        return entry

    remaining_profile = {key: value for key, value in profile.items() if key != "defaultSort"}
    updated = dict(entry)
    if remaining_profile:
        updated["profile"] = remaining_profile
    else:
        del updated["profile"]
    return updated
