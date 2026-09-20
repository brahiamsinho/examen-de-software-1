"""Pure `RelationalModel` -> manifest `dict` builder (design.md DD122, DD123)."""
from .manifest import ManifestError, build_manifest

__all__ = ["ManifestError", "build_manifest"]
