"""Generation must complete with no DB connection available and no
`relational_mapping`/`uml_modeling` validation routine invoked (spec:
Generator Purity requirement). Covers both public entry points:
`generate_table_sources` (per-`Table`) and `generate_shared_error_sources`
(per-project, DD42).
"""
from unittest.mock import patch

from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_shared_error_sources, generate_table_sources
from apps.spring_generator.tests.factories import a_table


def _product_table():
    return a_table(
        columns=(Column(name="id", type=ColumnType.UUID, nullable=False),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
    )


def test_generation_succeeds_with_no_db_access():
    # No `django_db`/`db` fixture is requested here: pytest-django
    # blocks any database access from a test that does not request it,
    # so a passing test already proves no DB connection was opened.
    sources = generate_table_sources(_product_table())

    assert len(sources.files) == 6


def test_generation_never_calls_the_validation_engine():
    with patch("apps.uml_modeling.validation.engine.validate") as mock_validate:
        generate_table_sources(_product_table())

    mock_validate.assert_not_called()


def test_shared_error_sources_generation_succeeds_with_no_db_access():
    # Same purity argument as above: no `django_db`/`db` fixture
    # requested, so a passing test already proves no DB connection.
    sources = generate_shared_error_sources(base_package="com.modelia.generated")

    assert len(sources.files) == 2


def test_shared_error_sources_generation_never_calls_the_validation_engine():
    with patch("apps.uml_modeling.validation.engine.validate") as mock_validate:
        generate_shared_error_sources(base_package="com.modelia.generated")

    mock_validate.assert_not_called()
