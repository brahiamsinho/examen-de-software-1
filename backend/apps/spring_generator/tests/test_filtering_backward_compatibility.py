from apps.relational_mapping.domain.profile import ColumnProfile
from apps.relational_mapping.domain.schema import Column
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_table_sources
from apps.spring_generator.tests.factories import a_table


def test_unset_profile_output_matches_no_profile_output_byte_identical():
    no_profile = a_table(name="product", columns=(Column(name="name", type=ColumnType.VARCHAR),))
    unset_profile = a_table(name="product", columns=(Column(name="name", type=ColumnType.VARCHAR, profile=ColumnProfile()),))

    assert generate_table_sources(unset_profile).files == generate_table_sources(no_profile).files


def test_false_searchable_sortable_output_matches_no_profile_output_byte_identical():
    no_profile = a_table(name="product", columns=(Column(name="name", type=ColumnType.VARCHAR),))
    false_profile = a_table(
        name="product",
        columns=(Column(name="name", type=ColumnType.VARCHAR, profile=ColumnProfile(searchable=False, sortable=False)),),
    )

    assert generate_table_sources(false_profile).files == generate_table_sources(no_profile).files
