"""Structural regression guard: `ai_assistant`'s source modules must import
only from `apps.uml_modeling`, `apps.uml_commands`, `apps.uml_documents`,
`apps.organizations`, the Python standard library, and
Django/ninja/pydantic/google/openai (the `google-genai` and `openai` SDKs,
the two selectable LLM providers — DD180). No import of `apps.users` or any
other feature app (`apps.relational_mapping`, `apps.generation_export`,
`apps.backend_deployments`, ...) is allowed — `ai_assistant` depends
downward only, the same direction `apps.relational_mapping`/
`apps.generation_export` already depend on `apps.uml_documents`.

Mirrors `apps.uml_documents.tests.test_import_boundary`.
"""
import ast
import pathlib
import sys

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent
_SCOPED_FILES = (
    _PACKAGE_DIR / "errors.py",
    _PACKAGE_DIR / "gemini_client.py",
    _PACKAGE_DIR / "openai_client.py",
    _PACKAGE_DIR / "llm_provider.py",
    _PACKAGE_DIR / "tools.py",
    _PACKAGE_DIR / "translator.py",
    _PACKAGE_DIR / "schemas.py",
    _PACKAGE_DIR / "service.py",
    _PACKAGE_DIR / "api.py",
)
_ALLOWED_PREFIXES = (
    "apps.uml_modeling",
    "apps.uml_commands",
    "apps.uml_documents",
    "apps.organizations",
    "apps.ai_assistant",  # self-package: these modules cross-import each other
    "django",
    "ninja",
    "pydantic",
    "google",  # google-genai SDK, imported lazily inside gemini_client.py
    "openai",  # openai SDK, imported lazily inside openai_client.py
)
_DISALLOWED_PREFIXES = ("apps.users",)


def _import_targets(source_path: pathlib.Path) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                targets.append(node.module)
    return targets


def _assert_import_allowed(source_name: str, target: str) -> None:
    top_level = target.split(".")[0]
    if top_level in sys.stdlib_module_names:
        return

    assert target.startswith(_ALLOWED_PREFIXES), (
        f"{source_name}: non-stdlib import {target!r} must start with "
        "'apps.uml_modeling', 'apps.uml_commands', 'apps.uml_documents', "
        "'apps.organizations', or Django/ninja/pydantic/google"
    )
    assert not any(target.startswith(prefix) for prefix in _DISALLOWED_PREFIXES), (
        f"{source_name}: disallowed import {target!r}"
    )


def test_no_disallowed_imports_exist():
    assert _SCOPED_FILES, "expected at least one scoped source file"

    for source_path in _SCOPED_FILES:
        for target in _import_targets(source_path):
            _assert_import_allowed(source_path.name, target)


def test_every_declared_scoped_file_exists():
    for source_path in _SCOPED_FILES:
        assert source_path.is_file(), f"missing scoped file: {source_path}"


def test_a_users_import_would_fail_the_guard():
    import pytest

    with pytest.raises(AssertionError):
        _assert_import_allowed("service.py", "apps.users.models")


def test_a_sibling_feature_app_import_would_fail_the_guard():
    import pytest

    with pytest.raises(AssertionError):
        _assert_import_allowed("service.py", "apps.relational_mapping.mapping.mapper")
    with pytest.raises(AssertionError):
        _assert_import_allowed("service.py", "apps.backend_deployments.runner_client")
