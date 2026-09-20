"""relational-generation-metadata: a generation profile carried by the mapper
must not change the Domain Manifest (relational-mapping spec, Requirement:
Profile Carry-Through Is Output-Neutral). Lives here because no other app may
import `apps.domain_manifest` (see `test_builder_decoupling.py`); the Spring
half of the scenario is `generation_runner/tests/test_profile_output_neutral.py`.
"""
import dataclasses

from apps.domain_manifest.builder import build_manifest
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


def test_declared_profile_does_not_change_the_domain_manifest():
    profiled = map_to_relational(_model_with_declared_profiles())

    assert any(table.profile is not None for table in profiled.tables)
    assert build_manifest(profiled) == build_manifest(map_to_relational(build_sample_model()))
