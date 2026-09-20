"""The manifest builder's single typed error (design.md DD143).

Lives in its own module so `entities.py` can raise it without importing
`manifest.py`, which itself imports `entities.py`.
"""


class ManifestError(ValueError):
    """The model holds a name the generator itself would reject, or an unresolvable declared reference."""
