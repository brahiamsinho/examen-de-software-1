"""Profile emission vs. neutrality (spec: Profile Emission Determinism and Sample Neutrality, DD149).

A declared generation profile changes the Domain Manifest; empty or absent metadata
does not, so the sample model (and the gate output) stays byte-identical. Lives here
because no other app may import `apps.domain_manifest` (see `test_builder_decoupling.py`);
the Spring half of the scenario is `generation_runner/tests/test_profile_output_neutral.py`.
"""
import dataclasses

from apps.domain_manifest.builder import build_manifest
from apps.domain_manifest.serialize import to_json_text
from apps.generation_runner.samples.sample_model import build_sample_model
from apps.relational_mapping.mapping.mapper import map_to_relational


def _model_with_declared_profiles():
    model = build_sample_model()
    metadata = {}
    for uml_class in model.classes:
        metadata[uml_class.id] = {
            "profile": {"auditable": True, "readOnly": False, "crud": ["read", "create"]}
        }
        for attribute in uml_class.attributes:
            metadata[attribute.id] = {"profile": {"searchable": True, "sortable": True}}
    return dataclasses.replace(model, generation_metadata=metadata)


def _sample_manifest():
    return build_manifest(map_to_relational(build_sample_model()))


def test_a_declared_profile_changes_the_domain_manifest():
    profiled = map_to_relational(_model_with_declared_profiles())

    assert any(table.profile is not None for table in profiled.tables)
    manifest = build_manifest(profiled)
    assert manifest != _sample_manifest()
    assert "\"profile\":" in to_json_text(manifest)


def test_empty_generation_metadata_leaves_the_manifest_unchanged():
    model = build_sample_model()
    empty = dataclasses.replace(model, generation_metadata={})
    empty_per_element = dataclasses.replace(
        model, generation_metadata={uml_class.id: {} for uml_class in model.classes}
    )

    assert build_manifest(map_to_relational(empty)) == _sample_manifest()
    assert build_manifest(map_to_relational(empty_per_element)) == _sample_manifest()
    assert "\"profile\":" not in to_json_text(_sample_manifest())
