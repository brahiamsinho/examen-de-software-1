import pytest

from apps.relational_mapping.domain.schema import RelationalModel
from apps.spring_generator.emit.errors import GeneratedSourcePathCollisionError, UngeneratableSourceError
from apps.spring_generator.emit.renderer import generate_model_sources
from apps.spring_generator.tests.factories import a_table, an_enum_type


def test_table_enum_exact_path_collision_raises_typed_error_with_payload():
    model = RelationalModel(
        tables=(a_table(name="status"),),
        enum_types=(an_enum_type(name="status", labels=("ACTIVE",)),),
    )

    with pytest.raises(GeneratedSourcePathCollisionError) as excinfo:
        generate_model_sources(model)

    assert isinstance(excinfo.value, UngeneratableSourceError)
    assert excinfo.value.path == "src/main/java/com/modelia/generated/domain/Status.java"
    assert excinfo.value.occurrences == 2


def test_duplicate_enum_normalized_path_collision_raises_typed_error():
    model = RelationalModel(
        enum_types=(
            an_enum_type(name="order_status", labels=("PENDING",)),
            an_enum_type(name="OrderStatus", labels=("PAID",)),
        )
    )

    with pytest.raises(GeneratedSourcePathCollisionError) as excinfo:
        generate_model_sources(model)

    assert excinfo.value.path == "src/main/java/com/modelia/generated/domain/OrderStatus.java"
    assert excinfo.value.occurrences == 2


def test_collision_failure_exposes_no_partial_aggregate():
    model = RelationalModel(
        tables=(a_table(name="status"),),
        enum_types=(an_enum_type(name="status", labels=("ACTIVE",)),),
    )

    with pytest.raises(GeneratedSourcePathCollisionError):
        generate_model_sources(model)


def test_first_collision_is_deterministic_by_candidate_scan_order():
    model = RelationalModel(
        tables=(a_table(name="status"), a_table(name="priority")),
        enum_types=(
            an_enum_type(name="status", labels=("ACTIVE",)),
            an_enum_type(name="priority", labels=("LOW",)),
        ),
    )

    with pytest.raises(GeneratedSourcePathCollisionError) as excinfo:
        generate_model_sources(model)

    assert excinfo.value.path == "src/main/java/com/modelia/generated/domain/Status.java"
    assert excinfo.value.occurrences == 2
