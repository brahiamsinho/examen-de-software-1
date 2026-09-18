"""Generation must complete with no DB connection available and no
`relational_mapping`/`uml_modeling` validation routine invoked (spec:
Generator Purity requirement).
"""
from unittest.mock import patch

from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_table_sources
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

    assert len(sources.files) == 2


def test_generation_never_calls_the_validation_engine():
    with patch("apps.uml_modeling.validation.engine.validate") as mock_validate:
        generate_table_sources(_product_table())

    mock_validate.assert_not_called()
