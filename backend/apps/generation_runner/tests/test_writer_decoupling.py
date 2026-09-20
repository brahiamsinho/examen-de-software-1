"""DD75/DD76 guard: the pure part of the runner app never touches the generator.

`writer/**` and `domain/**` must not import `apps.spring_generator`, so the
generator stays free of any writer edge (DD74) and the writer stays a pure
function of its arguments. The glue (`cli.py`, `runner_image.py`,
`samples/`) is deliberately outside this scan.
"""
import ast
import subprocess
import sys
from pathlib import Path

import apps.generation_runner as runner_package

RUNNER_ROOT = Path(runner_package.__file__).resolve().parent
GUARDED_DIRECTORIES = ("writer", "domain")
FORBIDDEN_PREFIX = "apps.spring_generator"
BACKEND_ROOT = RUNNER_ROOT.parent.parent


def _guarded_python_files() -> list[Path]:
    files: list[Path] = []
    for directory in GUARDED_DIRECTORIES:
        files.extend(sorted((RUNNER_ROOT / directory).rglob("*.py")))
    return files


def _imported_module_names(source: str) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.append(module)
            names.extend(f"{module}.{alias.name}" for alias in node.names)
    return names


def _names_forbidden_module(name: str) -> bool:
    return name == FORBIDDEN_PREFIX or name.startswith(FORBIDDEN_PREFIX + ".")


def test_guarded_directories_contain_python_files():
    for directory in GUARDED_DIRECTORIES:
        assert list((RUNNER_ROOT / directory).rglob("*.py")), f"{directory}/ has no python files"


def test_guarded_directories_never_import_the_generator():
    files = _guarded_python_files()
    assert len(files) >= 4  # domain/{__init__,errors,protocols} + writer/{__init__,filesystem}

    offenders = [
        f"{path.relative_to(RUNNER_ROOT)}: {name}"
        for path in files
        for name in _imported_module_names(path.read_text(encoding="utf-8"))
        if _names_forbidden_module(name)
    ]

    assert offenders == []


def test_scanner_flags_a_generator_import():
    # Triangulation: the scanner itself must detect both import forms.
    assert any(_names_forbidden_module(n) for n in _imported_module_names("import apps.spring_generator.emit"))
    assert any(
        _names_forbidden_module(n)
        for n in _imported_module_names("from apps.spring_generator.domain.sources import GeneratedSources")
    )
    assert not any(_names_forbidden_module(n) for n in _imported_module_names("from pathlib import Path"))


def test_importing_the_writer_does_not_load_the_generator():
    program = (
        "import sys\n"
        "import apps.generation_runner.writer\n"
        "print('apps.spring_generator' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
