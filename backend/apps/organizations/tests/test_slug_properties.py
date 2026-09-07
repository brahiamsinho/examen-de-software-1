"""Property-based tests for the pure slug/name derivation helpers
(organization-tenancy § Server-Generated Organization Slug).

No `django_db` fixture here: these functions are pure and DB-free by
design (design.md DD1), which is exactly what makes them
`hypothesis`-eligible without tripping `HealthCheck.function_scoped_fixture`.
"""
import re

from hypothesis import given
from hypothesis import strategies as st

from apps.organizations.services import build_slug_base, derive_workspace_name


@given(st.text(max_size=200))
def test_base_is_always_a_bounded_nonempty_url_safe_slug(source):
    base = build_slug_base(source=source)

    assert 1 <= len(base) <= 40
    assert re.fullmatch(r"[a-z0-9_-]+", base)
    assert len(f"{base}-{'0' * 6}") <= 47


@given(st.text(max_size=300))
def test_name_always_fits_and_keeps_its_suffix(source):
    name = derive_workspace_name(source=source)

    assert name.endswith("'s Workspace")
    assert len(name) <= 120
