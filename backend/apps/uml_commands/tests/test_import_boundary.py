"""Structural regression guard (DD7): `commands.py`, `dispatcher.py`, and
every `handlers/*.py` module must import only from `apps.uml_modeling`
and the Python standard library. No import of `django.*`,
`apps.organizations`, or `apps.users` is allowed.

`apps.py`/`__init__.py` are intentionally excluded — `apps.py` MUST
import `django.apps.AppConfig` to register as a Django app, matching
`apps.uml_modeling`'s own precedent (DD7). `tests/` legitimately imports
`pytest` (third-party, not stdlib/uml_modeling).

Not a RED-then-GREEN pair: this is a boundary check against source
already written in Phases 2-6, expected to pass immediately.
"""
import ast
import pathlib
import sys

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent
_SCOPED_FILES = (
    _PACKAGE_DIR / "commands.py",
    _PACKAGE_DIR / "dispatcher.py",
    *sorted((_PACKAGE_DIR / "handlers").glob("*.py")),
)
_DISALLOWED_PREFIXES = ("django", "apps.organizations", "apps.users")
_ALLOWED_PREFIXES = ("apps.uml_modeling", "apps.uml_commands")


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


def test_no_disallowed_imports_exist():
    assert _SCOPED_FILES, "expected at least one scoped source file"

    for source_path in _SCOPED_FILES:
        for target in _import_targets(source_path):
            top_level = target.split(".")[0]
            if top_level in sys.stdlib_module_names:
                continue

            # "apps.uml_commands" (self-package, e.g. dispatcher.py importing
            # its own handlers submodules) is intra-package, not "any other
            # app" per the spec's wording — it is not an external dependency
            # this boundary guards against.
            assert target.startswith(_ALLOWED_PREFIXES), (
                f"{source_path.name}: non-stdlib import {target!r} must start with "
                "'apps.uml_modeling' or 'apps.uml_commands' (self-package)"
            )
            assert not any(target.startswith(prefix) for prefix in _DISALLOWED_PREFIXES), (
                f"{source_path.name}: disallowed import {target!r}"
            )
