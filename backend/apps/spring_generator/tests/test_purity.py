"""Generation must complete with no DB connection available and no
`relational_mapping`/`uml_modeling` validation routine invoked (spec:
Generator Purity requirement). Covers both public entry points:
`generate_table_sources` (per-`Table`) and `generate_shared_error_sources`
(per-project, DD42).
"""
import os
from unittest.mock import patch

from apps.relational_mapping.domain.schema import Column, PrimaryKey, RelationalModel
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import (
    generate_model_sources,
    generate_project_config_sources,
    generate_shared_error_sources,
    generate_table_sources,
)
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


def test_project_config_generation_succeeds_with_no_db_access():
    # Same purity argument as above: no `django_db`/`db` fixture
    # requested, so a passing test already proves no DB connection.
    sources = generate_project_config_sources()

    assert [generated_file.path for generated_file in sources.files] == ["src/main/resources/application.yml"]


def test_project_config_generation_never_calls_the_validation_engine():
    with patch("apps.uml_modeling.validation.engine.validate") as mock_validate:
        generate_project_config_sources()

    mock_validate.assert_not_called()


def test_project_config_generation_does_not_inspect_environment_or_run_subprocesses():
    with patch("os.getenv") as mock_getenv, patch.object(os.environ, "get") as mock_environ_get, patch(
        "subprocess.run"
    ) as mock_run, patch("subprocess.Popen") as mock_popen, patch(
        "subprocess.check_call"
    ) as mock_check_call, patch(
        "subprocess.check_output"
    ) as mock_check_output:
        generate_project_config_sources()

    mock_getenv.assert_not_called()
    mock_environ_get.assert_not_called()
    mock_run.assert_not_called()
    mock_popen.assert_not_called()
    mock_check_call.assert_not_called()
    mock_check_output.assert_not_called()


def test_model_source_generation_succeeds_with_no_db_access():
    sources = generate_model_sources(RelationalModel(tables=(_product_table(),)))

    assert len(sources.files) == 9


def test_model_source_generation_never_calls_the_validation_engine():
    with patch("apps.uml_modeling.validation.engine.validate") as mock_validate:
        generate_model_sources(RelationalModel(tables=(_product_table(),)))

    mock_validate.assert_not_called()


def test_model_source_generation_does_not_inspect_environment_or_run_subprocesses():
    with patch("os.getenv") as mock_getenv, patch.object(os.environ, "get") as mock_environ_get, patch(
        "subprocess.run"
    ) as mock_run, patch("subprocess.Popen") as mock_popen, patch(
        "subprocess.check_call"
    ) as mock_check_call, patch(
        "subprocess.check_output"
    ) as mock_check_output:
        generate_model_sources(RelationalModel(tables=(_product_table(),)))

    mock_getenv.assert_not_called()
    mock_environ_get.assert_not_called()
    mock_run.assert_not_called()
    mock_popen.assert_not_called()
    mock_check_call.assert_not_called()
    mock_check_output.assert_not_called()
