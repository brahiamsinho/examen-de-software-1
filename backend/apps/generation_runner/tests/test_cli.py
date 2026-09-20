"""DD79: the CLI is a plain `__main__` module, no Django bootstrap.

Every case runs the real CLI in a subprocess from `backend/` with
`DJANGO_SETTINGS_MODULE` and `POSTGRES_*` removed from the environment, which
proves the one-shot compose service needs no `backend/.env`.
"""
import os
import subprocess
import sys
from pathlib import Path

import apps.generation_runner as runner_package

RUNNER_ROOT = Path(runner_package.__file__).resolve().parent
BACKEND_ROOT = RUNNER_ROOT.parent.parent
EXPECTED_FILE_COUNT = 41

TRAP_PROGRAM = (
    "import runpy, sys\n"
    "import django\n"
    "def _trap(*args, **kwargs):\n"
    "    raise AssertionError('django.setup was called')\n"
    "django.setup = _trap\n"
    "sys.argv = ['cli', '--target', sys.argv[1]]\n"
    "runpy.run_module('apps.generation_runner.cli', run_name='__main__')\n"
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
        [sys.executable, "-m", "apps.generation_runner.cli", *arguments],
        cwd=BACKEND_ROOT,
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=False,
    )


def _files_on_disk(directory: Path) -> list[Path]:
    return [path for path in directory.rglob("*") if path.is_file()]


def test_cli_writes_the_sample_project_and_exits_zero(tmp_path):
    target = tmp_path / "out"

    result = _run(["--target", str(target)])

    assert result.returncode == 0, result.stderr
    assert len(_files_on_disk(target)) == EXPECTED_FILE_COUNT
    assert (target / "build.gradle").is_file()
    assert (target / "settings.gradle").is_file()


def test_cli_uses_the_requested_base_package(tmp_path):
    target = tmp_path / "out"

    result = _run(["--target", str(target), "--base-package", "org.example.app"])

    assert result.returncode == 0, result.stderr
    assert (target / "src/main/java/org/example/app/Application.java").is_file()


def test_cli_refuses_a_non_empty_target_without_a_traceback(tmp_path):
    (tmp_path / "Old.java").write_text("stale", encoding="utf-8")

    result = _run(["--target", str(tmp_path)])

    assert result.returncode == 1
    assert "is not empty" in result.stderr
    assert "Traceback" not in result.stderr
    assert sorted(path.name for path in tmp_path.iterdir()) == ["Old.java"]
    assert (tmp_path / "Old.java").read_text(encoding="utf-8") == "stale"


def test_cli_requires_a_target_argument():
    result = _run([])

    assert result.returncode == 2
    assert "--target" in result.stderr


def test_cli_rejects_an_invalid_base_package_and_writes_nothing(tmp_path):
    target = tmp_path / "out"

    result = _run(["--target", str(target), "--base-package", "not a package!"])

    assert result.returncode == 1
    assert "base_package" in result.stderr
    assert "Traceback" not in result.stderr
    assert not target.exists()


def test_cli_never_calls_django_setup(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", TRAP_PROGRAM, str(tmp_path / "out")],
        cwd=BACKEND_ROOT,
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


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


def test_cli_source_has_no_django_import_and_no_container_path():
    source = (RUNNER_ROOT / "cli.py").read_text(encoding="utf-8")

    assert "import django" not in source
    assert "from django" not in source
    assert "/generated/project" not in source


def test_cli_reports_a_generator_error_without_a_traceback(monkeypatch, capsys, tmp_path):
    from apps.generation_runner import cli
    from apps.spring_generator.emit.errors import UngeneratableSourceError

    def _boom(*args, **kwargs):
        raise UngeneratableSourceError("cannot generate")

    monkeypatch.setattr(cli, "generate_project_sources", _boom)

    assert cli.main(["--target", str(tmp_path / "out")]) == 1
    assert "cannot generate" in capsys.readouterr().err


def test_cli_reports_an_operating_system_error_without_a_traceback(monkeypatch, capsys, tmp_path):
    from apps.generation_runner import cli

    def _boom(*args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(cli, "write_sources", _boom)

    assert cli.main(["--target", str(tmp_path / "out")]) == 1
    assert "disk unavailable" in capsys.readouterr().err
