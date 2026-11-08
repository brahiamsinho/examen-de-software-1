"""Structural regression guard (issue #17): `session_log` is a low-level app.
Its modules may import only from `apps.organizations`, `apps.uml_commands`
(to describe a command), itself, the standard library and Django/ninja. It must
never import `apps.uml_documents`, `apps.ai_assistant` or `apps.users`: those
apps import IT to record what happens, so importing them back would make a cycle.
The diagram's model is looked up by name (`django.apps.apps.get_model`).
"""
import ast
import pathlib
import sys

import pytest

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent
_SCOPED_FILES = tuple(
    _PACKAGE_DIR / name for name in ("models.py", "services.py", "schemas.py", "api.py")
)
_ALLOWED_PREFIXES = ("apps.organizations", "apps.uml_commands", "apps.session_log", "django", "ninja")
_DISALLOWED_PREFIXES = ("apps.uml_documents", "apps.ai_assistant", "apps.users")


def _import_targets(source_path: pathlib.Path) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            targets.append(node.module)
    return targets


def _assert_import_allowed(source_name: str, target: str) -> None:
    if target.split(".")[0] in sys.stdlib_module_names:
        return
    assert target.startswith(_ALLOWED_PREFIXES), f"{source_name}: import {target!r} is not allowed here"
    assert not target.startswith(_DISALLOWED_PREFIXES), f"{source_name}: disallowed import {target!r}"


def test_the_session_log_imports_only_what_a_low_level_app_may():
    for source_path in _SCOPED_FILES:
        for target in _import_targets(source_path):
            _assert_import_allowed(source_path.name, target)


@pytest.mark.parametrize(
    "target", ["apps.uml_documents.services", "apps.ai_assistant.chat", "apps.users.models", "apps.relational_mapping"]
)
def test_importing_a_feature_app_would_fail_the_guard(target):
    with pytest.raises(AssertionError):
        _assert_import_allowed("services.py", target)
