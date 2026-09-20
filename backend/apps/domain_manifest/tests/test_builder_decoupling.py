"""DD121/DD123/DD124 guard: the builder is pure, and only `emit.naming` is shared.

`builder/**` and `serialize.py` may import `apps.spring_generator.emit.naming`
and nothing else from `apps.*` or Django. `cli.py` is glue: it may also import
the sample model. No other app may import `apps.domain_manifest`.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

import apps.domain_manifest as manifest_package
import pytest
from django.apps import apps
from django.conf import settings

ROOT = Path(manifest_package.__file__).resolve().parent
BACKEND_ROOT = ROOT.parent.parent
NAMING = ("apps.spring_generator.emit.naming",)
CLI_ALLOWED = ("apps.domain_manifest", "apps.generation_runner.samples.sample_model")
URL_OR_HOST_PATTERN = re.compile(r"https?://|localhost|127\.0\.0\.1|0\.0\.0\.0|\b[a-z][a-z0-9.-]*:\d{2,5}\b")


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


def _within(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)


def _offenders(source: str, allowed: tuple[str, ...]) -> list[str]:
    return [
        name
        for name in _imported_module_names(source)
        if _within(name, ("django", "apps")) and not _within(name, allowed)
    ]


def _guarded_files() -> list[Path]:
    return sorted((ROOT / "builder").rglob("*.py")) + [ROOT / "serialize.py"]


def _source_files() -> list[Path]:
    return [path for path in sorted(ROOT.rglob("*.py")) if "tests" not in path.relative_to(ROOT).parts]


@pytest.mark.parametrize(
    ("source", "flagged"),
    [
        ("import django.conf", True),
        ("from apps.generation_runner.writer import write_sources", True),
        ("from apps.postman_export.converter import build_collection", True),
        ("from apps.uml_modeling.domain.ids import ElementId", True),
        ("from apps.relational_mapping.domain.types import ColumnType", True),
        ("from apps.spring_generator.emit.context import build_context", True),
        ("from apps.spring_generator.emit.naming import pascal_case", False),
        ("import json, argparse\nfrom .attributes import build_attributes", False),
    ],
)
def test_builder_scanner_allows_only_the_naming_module(source, flagged):
    assert bool(_offenders(source, NAMING)) is flagged


def test_builder_and_serializer_import_only_the_naming_module():
    files = _guarded_files()

    assert ROOT / "builder" / "__init__.py" in files and ROOT / "serialize.py" in files
    assert [f"{path.name}: {name}" for path in files for name in _offenders(path.read_text("utf-8"), NAMING)] == []


def test_cli_imports_only_its_own_app_and_the_sample_model():
    cli_module = ROOT / "cli.py"

    assert _offenders(cli_module.read_text("utf-8"), CLI_ALLOWED) == []
    assert _offenders("from apps.postman_export.cli import main", CLI_ALLOWED) != []


def test_importing_the_builder_loads_neither_django_nor_jinja_nor_the_runner():
    program = (
        "import sys\n"
        "import apps.domain_manifest.builder, apps.domain_manifest.serialize\n"
        "print([m for m in ('django', 'jinja2', 'apps.generation_runner') if m in sys.modules])\n"
    )
    result = subprocess.run([sys.executable, "-c", program], cwd=BACKEND_ROOT, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


def test_no_other_app_imports_the_manifest_app():
    offenders = [
        str(path.relative_to(BACKEND_ROOT))
        for path in sorted(BACKEND_ROOT.rglob("*.py"))
        if ROOT not in path.parents
        for name in _imported_module_names(path.read_text(encoding="utf-8"))
        if _within(name, ("apps.domain_manifest",))
    ]

    assert offenders == []


def test_app_is_registered_right_after_postman_export_without_models_or_migrations():
    installed = list(settings.INSTALLED_APPS)

    assert installed.index("apps.domain_manifest") == installed.index("apps.postman_export") + 1
    assert apps.get_app_config("domain_manifest").name == "apps.domain_manifest"
    assert not (ROOT / "models.py").exists() and not (ROOT / "migrations").exists()


def test_source_has_no_host_port_or_url_literal():
    literals = [
        node.value
        for path in _source_files()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and URL_OR_HOST_PATTERN.search(node.value)
    ]

    assert literals == []
