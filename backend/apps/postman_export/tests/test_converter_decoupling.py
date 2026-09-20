"""DD109/DD110 guard: the converter and its CLI are pure and self-contained.

`converter/**` and `cli.py` must not import Django or the generator apps, no
other app may import `apps.postman_export`, and no host, port or URL literal
(other than the single Postman schema URL) may live in the app source. The
scan covers non-test source only; tests may carry provenance notes.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

import apps.postman_export as export_package
from django.apps import apps
from django.conf import settings

EXPORT_ROOT = Path(export_package.__file__).resolve().parent
BACKEND_ROOT = EXPORT_ROOT.parent.parent
FORBIDDEN_PREFIXES = ("django", "apps.spring_generator", "apps.generation_runner")
POSTMAN_SCHEMA_URL = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
URL_OR_HOST_PATTERN = re.compile(r"https?://|localhost|127\.0\.0\.1|0\.0\.0\.0|\b[a-z][a-z0-9.-]*:\d{2,5}\b")
SPRINGDOC_VERSION = "3.1.1"


def _guarded_python_files() -> list[Path]:
    files = sorted((EXPORT_ROOT / "converter").rglob("*.py"))
    cli_module = EXPORT_ROOT / "cli.py"
    return files + [cli_module] if cli_module.is_file() else files


def _source_python_files() -> list[Path]:
    return [path for path in sorted(EXPORT_ROOT.rglob("*.py")) if "tests" not in path.relative_to(EXPORT_ROOT).parts]


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


def _names_prefix(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)


def _string_literals(source: str) -> list[str]:
    return [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_guarded_files_exist():
    # cli.py joins the scan once it exists (its own behaviour is pinned in test_cli.py).
    files = _guarded_python_files()

    assert EXPORT_ROOT / "converter" / "__init__.py" in files


def test_converter_and_cli_never_import_django_or_the_generator_apps():
    offenders = [
        f"{path.relative_to(EXPORT_ROOT)}: {name}"
        for path in _guarded_python_files()
        for name in _imported_module_names(path.read_text(encoding="utf-8"))
        if _names_prefix(name, FORBIDDEN_PREFIXES)
    ]

    assert offenders == []


def test_scanner_flags_django_and_generator_imports_but_not_stdlib():
    # Triangulation: the scanner must detect both import forms.
    assert any(_names_prefix(n, FORBIDDEN_PREFIXES) for n in _imported_module_names("import django.conf"))
    assert any(
        _names_prefix(n, FORBIDDEN_PREFIXES)
        for n in _imported_module_names("from apps.generation_runner.writer import write_sources")
    )
    assert not any(_names_prefix(n, FORBIDDEN_PREFIXES) for n in _imported_module_names("import json, argparse"))


def test_importing_the_converter_does_not_load_django_or_the_generators():
    program = (
        "import sys\n"
        "import apps.postman_export.converter\n"
        "print([m for m in ('django', 'apps.spring_generator', 'apps.generation_runner') if m in sys.modules])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", program], cwd=BACKEND_ROOT, capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


def test_no_other_app_imports_the_export_app():
    offenders = [
        str(path.relative_to(BACKEND_ROOT))
        for path in sorted(BACKEND_ROOT.rglob("*.py"))
        if EXPORT_ROOT not in path.parents
        for name in _imported_module_names(path.read_text(encoding="utf-8"))
        if _names_prefix(name, ("apps.postman_export",))
    ]

    assert offenders == []


def test_app_is_registered_in_installed_apps_after_the_generation_runner():
    installed = list(settings.INSTALLED_APPS)

    assert "apps.postman_export" in installed
    assert installed.index("apps.postman_export") > installed.index("apps.generation_runner")
    assert apps.get_app_config("postman_export").name == "apps.postman_export"


def test_source_has_no_host_port_or_url_literal_besides_the_schema_url():
    literals = [
        literal
        for path in _source_python_files()
        for literal in _string_literals(path.read_text(encoding="utf-8"))
        if URL_OR_HOST_PATTERN.search(literal) and literal != POSTMAN_SCHEMA_URL
    ]

    assert literals == []


def test_source_never_restates_the_springdoc_version():
    offenders = [
        path.name for path in _source_python_files() if SPRINGDOC_VERSION in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_the_literal_pattern_flags_hosts_and_ports_but_not_timestamps():
    # Triangulation: the guard must reject hosts/ports yet allow the date-time example.
    assert URL_OR_HOST_PATTERN.search("http://example.test/api")
    assert URL_OR_HOST_PATTERN.search("localhost")
    assert URL_OR_HOST_PATTERN.search("db:5432")
    assert not URL_OR_HOST_PATTERN.search("2024-01-01T00:00:00Z")
