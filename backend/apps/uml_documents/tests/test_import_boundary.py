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

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent
_SCOPED_FILES = (
    _PACKAGE_DIR / "models.py",
    _PACKAGE_DIR / "codec.py",
    _PACKAGE_DIR / "services.py",
    _PACKAGE_DIR / "schemas.py",
    _PACKAGE_DIR / "errors.py",
)
_DISALLOWED_PREFIXES = ("apps.users",)
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


def test_no_disallowed_imports_exist():
    assert _SCOPED_FILES, "expected at least one scoped source file"

    for source_path in _SCOPED_FILES:
        for target in _import_targets(source_path):
            top_level = target.split(".")[0]
            if top_level in sys.stdlib_module_names:
                continue

            assert target.startswith(_ALLOWED_PREFIXES), (
                f"{source_path.name}: non-stdlib import {target!r} must start with "
                "'apps.uml_modeling', 'apps.uml_commands', 'apps.uml_documents' "
                "(self-package), or Django/ninja/pydantic"
            )
            assert not any(target.startswith(prefix) for prefix in _DISALLOWED_PREFIXES), (
                f"{source_path.name}: disallowed import {target!r}"
            )
