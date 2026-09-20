"""relational-generation-metadata: carrying a generation profile through the
mapper must not change any generated output (relational-mapping spec,
Requirement: Profile Carry-Through Is Output-Neutral).

The same sample model is mapped twice, with and without declared profiles;
the Spring sources must be identical (the Domain Manifest half lives in
`domain_manifest/tests/test_profile_output_neutral.py`, since no other app may
import the manifest app). No consumer reads `Table.profile` / `Column.profile` yet.
"""
import dataclasses

from apps.generation_runner.samples.sample_model import build_sample_model
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.spring_generator.emit.renderer import generate_project_sources

BASE_PACKAGE = "com.modelia.generated"


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


def test_declared_profiles_are_actually_carried_by_the_mapper():
    relational = map_to_relational(_model_with_declared_profiles())

    assert all(table.profile is not None for table in relational.tables if table.source_class_ids)
    assert any(column.profile is not None for table in relational.tables for column in table.columns)


def test_declared_profile_does_not_change_spring_sources():
    plain = map_to_relational(build_sample_model())
    profiled = map_to_relational(_model_with_declared_profiles())

    assert generate_project_sources(profiled, base_package=BASE_PACKAGE) == generate_project_sources(
        plain, base_package=BASE_PACKAGE
    )
