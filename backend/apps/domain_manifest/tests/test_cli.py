"""CLI contract (spec: CLI Contract). Plain `__main__`: no Django bootstrap.

Every case runs the real CLI in a subprocess from `backend/` with
`DJANGO_SETTINGS_MODULE` and `POSTGRES_*` removed (mirrors `postman_export/tests/test_cli.py`).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import apps.domain_manifest as manifest_package
import pytest

BACKEND_ROOT = Path(manifest_package.__file__).resolve().parent.parent.parent
MANIFEST_NAME = "domain-manifest.json"
TRAP_PROGRAM = (
    "import runpy, sys\n"
    "import django\n"
    "def _trap(*args, **kwargs):\n"
    "    raise AssertionError('django.setup was called')\n"
    "django.setup = _trap\n"
    "sys.argv = ['cli', '--out-dir', sys.argv[1]]\n"
    "runpy.run_module('apps.domain_manifest.cli', run_name='__main__')\n"
)
CONTROL_PROGRAM = TRAP_PROGRAM.split("sys.argv")[0] + "django.setup()\n"


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE" and not k.startswith("POSTGRES_")}


def _python(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *arguments], cwd=BACKEND_ROOT, env=_clean_env(), capture_output=True, text=True, check=False
    )


def _cli(*arguments: str) -> subprocess.CompletedProcess:
    return _python("-m", "apps.domain_manifest.cli", *arguments)


def test_success_creates_the_out_dir_and_writes_only_the_manifest(tmp_path):
    out_dir = tmp_path / "nested" / "docs"

    result = _cli("--out-dir", str(out_dir))

    assert result.returncode == 0, result.stderr
    assert [path.name for path in out_dir.rglob("*") if path.is_file()] == [MANIFEST_NAME]
    manifest = json.loads((out_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["schemaVersion"] == 1 and len(manifest["entities"]) == 6


def test_two_runs_produce_byte_identical_files(tmp_path):
    assert _cli("--out-dir", str(tmp_path / "first")).returncode == 0
    assert _cli("--out-dir", str(tmp_path / "second")).returncode == 0

    assert (tmp_path / "first" / MANIFEST_NAME).read_bytes() == (tmp_path / "second" / MANIFEST_NAME).read_bytes()


def test_unwritable_out_dir_exits_one_with_a_message_and_writes_nothing(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a regular file", encoding="utf-8")

    result = _cli("--out-dir", str(blocker / "docs"))

    assert result.returncode == 1
    assert "error:" in result.stderr and "blocker" in result.stderr
    assert "Traceback" not in result.stderr
    assert sorted(path.name for path in tmp_path.iterdir()) == ["blocker"]
    assert blocker.read_text(encoding="utf-8") == "a regular file"


def test_missing_out_dir_exits_two_naming_the_argument():
    result = _cli()

    assert result.returncode == 2
    assert "--out-dir" in result.stderr


@pytest.mark.parametrize(
    ("program", "expected_code", "expected_text"),
    [(TRAP_PROGRAM, 0, ""), (CONTROL_PROGRAM, 1, "django.setup was called")],
    ids=["cli never calls django.setup", "control: the trap fires when setup is called"],
)
def test_django_setup_trap(program, expected_code, expected_text, tmp_path):
    result = _python("-c", program, str(tmp_path / "out"))

    assert (result.returncode == 0) == (expected_code == 0), result.stderr
    assert expected_text in result.stderr
    assert (tmp_path / "out" / MANIFEST_NAME).is_file() == (expected_code == 0)
