"""Structural regression guard (DD1): `models.py`, `codec.py`,
`services.py`, and `schemas.py` must import only from `apps.uml_modeling`,
`apps.uml_commands`, `apps.organizations`, the Python standard library, and
Django/ninja/pydantic/channels/asgiref. No import of `apps.users` is allowed.

`channels`/`asgiref` were added to the allowlist by the
`realtime-uml-collaboration` cycle (design.md DD2/DD3): `services.py`'s
`broadcast_document` calls `channels.layers.get_channel_layer()` (wrapped
by `asgiref.sync.async_to_sync`, since channel layers are async-only) from
inside the `transaction.on_commit` callback — this is the one seam where
the persistence layer talks to the realtime transport, by design.

`apps.organizations` is *allowed*, not forbidden: `uml_documents` is a real
persisted, tenant-scoped Django app (structurally the same kind of app as
`apps/organizations` itself), not a pure-domain app like `uml_commands` —
`TenantScopedModel`, `TenantScopedManager`, `resolve_membership`,
`require_role`, and `Role` all live only in `apps.organizations`, so this
dependency is required, not a boundary violation (spec.md's Import Boundary
requirement was corrected to reflect this).

`api.py` is excluded from the scoped file set the same way `uml_commands`'
own `test_import_boundary.py` excludes `apps.py`/`__init__.py`: its
`resolve_membership`/`require_role`/`Role` imports are the same
`apps.organizations` dependency already allowed for `models.py`, not a
separate concern.

Mirrors `apps.uml_commands.tests.test_import_boundary`. Expected to pass
immediately against Phases 1-5's source.
"""
import ast
import pathlib
import sys

import pytest

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent
_SCOPED_FILES = (
    _PACKAGE_DIR / "models.py",
    _PACKAGE_DIR / "codec.py",
    _PACKAGE_DIR / "services.py",
    _PACKAGE_DIR / "schemas.py",
    _PACKAGE_DIR / "errors.py",
)
_DISALLOWED_PREFIXES = ("apps.users", "apps.relational_mapping")
# DD154: the single named exception. services.py calls the strict §33 parser at
# write time so write-time and generation-time rules cannot drift. Exact match
# only: a prefix allowance would admit mapper/schema and the rest of the app.
_ALLOWED_EXACT_MODULES = ("apps.relational_mapping.mapping.profile_parser",)
_ALLOWED_PREFIXES = (
    "apps.uml_modeling",
    "apps.uml_commands",
    "apps.organizations",
    "apps.uml_documents",
    "django",
    "ninja",
    "pydantic",
    "channels",
    "asgiref",
)


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
    if target in _ALLOWED_EXACT_MODULES:
        return

    assert target.startswith(_ALLOWED_PREFIXES), (
        f"{source_name}: non-stdlib import {target!r} must start with "
        "'apps.uml_modeling', 'apps.uml_commands', 'apps.uml_documents' "
        "(self-package), or Django/ninja/pydantic"
    )
    assert not any(target.startswith(prefix) for prefix in _DISALLOWED_PREFIXES), (
        f"{source_name}: disallowed import {target!r}"
    )


def test_no_disallowed_imports_exist():
    assert _SCOPED_FILES, "expected at least one scoped source file"

    for source_path in _SCOPED_FILES:
        for target in _import_targets(source_path):
            _assert_import_allowed(source_path.name, target)


def test_relational_mapping_exception_is_exactly_one_module():
    assert _ALLOWED_EXACT_MODULES == ("apps.relational_mapping.mapping.profile_parser",)


def test_the_allowed_relational_mapping_module_passes_the_guard():
    _assert_import_allowed("services.py", "apps.relational_mapping.mapping.profile_parser")


@pytest.mark.parametrize(
    "target",
    [
        "apps.relational_mapping.mapping.mapper",
        "apps.relational_mapping.mapping.errors",
        "apps.relational_mapping",
        "apps.users.models",
    ],
)
def test_any_other_relational_mapping_or_users_import_still_fails(target):
    with pytest.raises(AssertionError):
        _assert_import_allowed("services.py", target)


def _defined_names(source_path: pathlib.Path) -> set[str]:
    """Every class, function, and top-level assignment name the module defines."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return names


def test_command_semantics_stay_in_uml_commands():
    """uml_documents may only construct commands and call `dispatcher.apply`:
    no command dataclass, handler function, or dispatcher registration may be
    defined in its persistence/transport modules.
    """
    import inspect
    import typing

    from apps.uml_commands import commands
    from apps.uml_commands.handlers import (
        attributes,
        classes,
        generation_profile,
        operations,
        relationships,
    )

    forbidden = {member.__name__ for member in typing.get_args(commands.UmlCommand)}
    forbidden |= {"_HANDLERS", "Handler", "apply"}
    for module in (attributes, classes, generation_profile, operations, relationships):
        forbidden |= {
            name
            for name, function in inspect.getmembers(module, inspect.isfunction)
            if function.__module__ == module.__name__
        }

    for source_path in _SCOPED_FILES:
        offending = _defined_names(source_path) & forbidden
        assert not offending, f"{source_path.name} defines command semantics: {sorted(offending)}"
