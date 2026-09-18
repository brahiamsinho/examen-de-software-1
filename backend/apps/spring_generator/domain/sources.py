"""Frozen, DB-free, filesystem-free output shape of `generate_table_sources`
(design.md DD3, DD4). This is the sole return type of
`emit.renderer.generate_table_sources`. Zero Django, DB driver, or
Java/Spring Boot tooling imports.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class GeneratedFile:
    path: str          # POSIX-relative, e.g. "src/main/java/com/modelia/generated/domain/Order.java"
    contents: str


@dataclass(frozen=True)
class GeneratedSources:
    files: tuple[GeneratedFile, ...] = ()

    def as_mapping(self) -> Mapping[str, str]:
        """Derived, insertion-ordered view over `files` (DD4)."""
        return MappingProxyType({generated_file.path: generated_file.contents for generated_file in self.files})

    def file_by_path(self, path: str) -> GeneratedFile | None:
        for generated_file in self.files:
            if generated_file.path == path:
                return generated_file
        return None
