"""CLI contract (spec: CLI Contract). Plain `__main__`: no Django bootstrap.

Every case runs the real CLI in a subprocess from `backend/` with
`DJANGO_SETTINGS_MODULE` and `POSTGRES_*` removed from the environment, which
proves the one-shot compose service needs no `backend/.env` (mirrors
`generation_runner/tests/test_cli.py`).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import apps.postman_export as export_package

BACKEND_ROOT = Path(export_package.__file__).resolve().parent.parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "api-docs.json"
COLLECTION_NAME = "postman_collection.json"
ENVIRONMENT_NAME = "postman_environment.json"
SENTINEL_BASE_URL = "sentinel-base-url-value"

TRAP_PROGRAM = (
    "import runpy, sys\n"
    "import django\n"
    "def _trap(*args, **kwargs):\n"
    "    raise AssertionError('django.setup was called')\n"
    "django.setup = _trap\n"
    "sys.argv = ['cli', '--openapi', sys.argv[1], '--out-dir', sys.argv[2]]\n"
    "runpy.run_module('apps.postman_export.cli', run_name='__main__')\n"
)
CONTROL_PROGRAM = (
    "import django\n"
    "def _trap(*args, **kwargs):\n"
    "    raise AssertionError('django.setup was called')\n"
    "django.setup = _trap\n"
    "django.setup()\n"
)


def _clean_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key != "DJANGO_SETTINGS_MODULE" and not key.startswith("POSTGRES_")
    }


def _run(arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "apps.postman_export.cli", *arguments],
        cwd=BACKEND_ROOT,
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=False,
    )


def _files_on_disk(directory: Path) -> list[Path]:
    return [path for path in directory.rglob("*") if path.is_file()]


def _assert_clean_failure(result: subprocess.CompletedProcess, out_dir: Path, fragment: str) -> None:
    assert result.returncode == 1
    assert fragment in result.stderr
    assert "Traceback" not in result.stderr
    assert not out_dir.exists() or _files_on_disk(out_dir) == []


def test_success_writes_both_files_and_creates_the_out_dir(tmp_path):
    out_dir = tmp_path / "nested" / "docs"

    result = _run(["--openapi", str(FIXTURE), "--out-dir", str(out_dir)])

    assert result.returncode == 0, result.stderr
    assert sorted(path.name for path in _files_on_disk(out_dir)) == [COLLECTION_NAME, ENVIRONMENT_NAME]
    collection = json.loads((out_dir / COLLECTION_NAME).read_text(encoding="utf-8"))
    environment = json.loads((out_dir / ENVIRONMENT_NAME).read_text(encoding="utf-8"))
    assert collection["info"]["name"] == "OpenAPI definition"
    assert len(collection["item"]) == 5
    assert environment["values"] == [{"key": "baseUrl", "value": "", "enabled": True}]


def test_base_url_lands_only_in_the_environment_file(tmp_path):
    result = _run(["--openapi", str(FIXTURE), "--out-dir", str(tmp_path), "--base-url", SENTINEL_BASE_URL])

    assert result.returncode == 0, result.stderr
    assert SENTINEL_BASE_URL in (tmp_path / ENVIRONMENT_NAME).read_text(encoding="utf-8")
    assert SENTINEL_BASE_URL not in (tmp_path / COLLECTION_NAME).read_text(encoding="utf-8")


def test_two_runs_produce_byte_identical_files(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"

    assert _run(["--openapi", str(FIXTURE), "--out-dir", str(first)]).returncode == 0
    assert _run(["--openapi", str(FIXTURE), "--out-dir", str(second)]).returncode == 0

    for name in (COLLECTION_NAME, ENVIRONMENT_NAME):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_missing_input_file_exits_one_with_a_message(tmp_path):
    out_dir = tmp_path / "out"

    result = _run(["--openapi", str(tmp_path / "missing.json"), "--out-dir", str(out_dir)])

    _assert_clean_failure(result, out_dir, "missing.json")


def test_non_json_input_exits_one_with_a_message(tmp_path):
    source = tmp_path / "broken.json"
    source.write_text("{not json", encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run(["--openapi", str(source), "--out-dir", str(out_dir)])

    _assert_clean_failure(result, out_dir, "not valid JSON")


def test_document_without_paths_exits_one_with_a_message(tmp_path):
    source = tmp_path / "empty.json"
    source.write_text(json.dumps({"openapi": "3.1.0", "info": {"title": "T"}}), encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run(["--openapi", str(source), "--out-dir", str(out_dir)])

    _assert_clean_failure(result, out_dir, "paths")


def test_json_that_is_not_an_object_exits_one(tmp_path):
    source = tmp_path / "list.json"
    source.write_text("[]", encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run(["--openapi", str(source), "--out-dir", str(out_dir)])

    _assert_clean_failure(result, out_dir, "paths")


def test_unwritable_out_dir_exits_one_and_writes_nothing(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a regular file", encoding="utf-8")

    result = _run(["--openapi", str(FIXTURE), "--out-dir", str(blocker / "docs")])

    assert result.returncode == 1
    assert "blocker" in result.stderr
    assert "Traceback" not in result.stderr
    assert sorted(path.name for path in tmp_path.iterdir()) == ["blocker"]
    assert blocker.read_text(encoding="utf-8") == "a regular file"


def test_missing_arguments_exit_two_naming_the_argument(tmp_path):
    no_openapi = _run(["--out-dir", str(tmp_path)])
    no_out_dir = _run(["--openapi", str(FIXTURE)])

    assert no_openapi.returncode == 2
    assert "--openapi" in no_openapi.stderr
    assert no_out_dir.returncode == 2
    assert "--out-dir" in no_out_dir.stderr


def test_cli_never_calls_django_setup(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", TRAP_PROGRAM, str(FIXTURE), str(tmp_path / "out")],
        cwd=BACKEND_ROOT,
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out" / COLLECTION_NAME).is_file()


def test_the_django_setup_trap_really_fires_when_setup_is_called():
    # Control for the test above: without this the trap could be a no-op.
    result = subprocess.run(
        [sys.executable, "-c", CONTROL_PROGRAM],
        cwd=BACKEND_ROOT,
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "django.setup was called" in result.stderr


def test_a_shape_the_converter_cannot_handle_exits_one_without_a_traceback(tmp_path):
    source = tmp_path / "odd.json"
    source.write_text(json.dumps({"info": {"title": "T"}, "paths": {"/a": "not an object"}}), encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run(["--openapi", str(source), "--out-dir", str(out_dir)])

    _assert_clean_failure(result, out_dir, "cannot convert")
