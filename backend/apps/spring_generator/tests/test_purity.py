"""Generation must complete with no DB connection available and no
`relational_mapping`/`uml_modeling` validation routine invoked (spec:
Generator Purity requirement). Covers both public entry points:
`generate_table_sources` (per-`Table`) and `generate_shared_error_sources`
(per-project, DD42).
"""
import builtins
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.relational_mapping.domain.schema import Column, PrimaryKey, RelationalModel
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import (
    generate_model_sources,
    generate_project_config_sources,
    generate_project_scaffold_sources,
    generate_project_sources,
    generate_shared_error_sources,
    generate_table_sources,
)
from apps.spring_generator.tests.factories import a_table

_FORBIDDEN_CALL_TARGETS = (
    "os.getenv",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_call",
    "subprocess.check_output",
    "socket.socket",
    "socket.create_connection",
    "os.makedirs",
    "os.mkdir",
)


@contextmanager
def _runtime_free_guard():
    """Patch every runtime boundary the scaffold entry points must not touch.

    Reads cannot be blocked: Jinja lazily reads the packaged `.j2` files on
    first render. Writes can: `open` in a writing mode and the `Path` write and
    mkdir helpers raise. Everything else is a mock the caller asserts on.
    """
    real_open = builtins.open

    def _write_rejecting_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            raise AssertionError("filesystem write attempted: open({!r}, {!r})".format(file, mode))
        return real_open(file, mode, *args, **kwargs)

    def _rejected_path_write(*args, **kwargs):
        raise AssertionError("filesystem write attempted through pathlib")

    with ExitStack() as stack:
        mocks = {target: stack.enter_context(patch(target)) for target in _FORBIDDEN_CALL_TARGETS}
        mocks["os.environ.get"] = stack.enter_context(patch.object(os.environ, "get"))
        stack.enter_context(patch("builtins.open", _write_rejecting_open))
        for method in ("write_text", "write_bytes", "mkdir"):
            stack.enter_context(patch.object(Path, method, _rejected_path_write))
        yield mocks


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


def test_runtime_free_guard_rejects_a_filesystem_write(tmp_path):
    # Non-vacuity: the guard the scaffold tests rely on must really fire.
    with _runtime_free_guard():
        with pytest.raises(AssertionError):
            open(tmp_path / "out.txt", "w")
        with pytest.raises(AssertionError):
            Path(tmp_path / "out.txt").write_text("x")
        with pytest.raises(AssertionError):
            Path(tmp_path / "dir").mkdir()

    assert not (tmp_path / "out.txt").exists()
    assert not (tmp_path / "dir").exists()


def test_runtime_free_guard_records_subprocess_environment_and_socket_use():
    with _runtime_free_guard() as mocks:
        import socket
        import subprocess

        subprocess.run(["true"])
        os.getenv("ANYTHING")
        socket.create_connection(("host", 1))

    mocks["subprocess.run"].assert_called_once()
    mocks["os.getenv"].assert_called_once()
    mocks["socket.create_connection"].assert_called_once()


def test_project_scaffold_generation_succeeds_with_no_db_access():
    # No `django_db`/`db` fixture requested: a pass proves no DB connection.
    sources = generate_project_scaffold_sources(base_package="com.modelia.generated")

    assert [generated_file.path for generated_file in sources.files] == [
        "build.gradle",
        "settings.gradle",
        "src/main/java/com/modelia/generated/Application.java",
    ]


def test_project_generation_succeeds_with_no_db_access():
    sources = generate_project_sources(RelationalModel(tables=(_product_table(),)))

    assert len(sources.files) == 12


def test_project_scaffold_generation_never_calls_the_validation_engine():
    with patch("apps.uml_modeling.validation.engine.validate") as mock_validate:
        generate_project_scaffold_sources(base_package="com.modelia.generated")

    mock_validate.assert_not_called()


def test_project_generation_never_calls_the_validation_engine():
    with patch("apps.uml_modeling.validation.engine.validate") as mock_validate:
        generate_project_sources(RelationalModel(tables=(_product_table(),)))

    mock_validate.assert_not_called()


def _assert_no_runtime_boundary_touched(mocks):
    for target, mock in mocks.items():
        assert not mock.called, "{} was called".format(target)


def test_project_scaffold_generation_touches_no_runtime_boundary():
    with _runtime_free_guard() as mocks:
        sources = generate_project_scaffold_sources(base_package="com.modelia.generated")

    assert len(sources.files) == 3
    _assert_no_runtime_boundary_touched(mocks)


def test_project_generation_touches_no_runtime_boundary():
    with _runtime_free_guard() as mocks:
        sources = generate_project_sources(RelationalModel(tables=(_product_table(),)))

    assert len(sources.files) == 12
    _assert_no_runtime_boundary_touched(mocks)
