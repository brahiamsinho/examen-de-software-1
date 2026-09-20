"""Structural input types of the writer (design.md DD76).

`typing.Protocol` gives full static checking with zero import edge to
`apps.spring_generator`, which is what lets the DD75 guard pass. Not
`runtime_checkable`: `isinstance` on a Protocol only checks attribute
presence, which buys nothing over the validation `write_sources` performs.
"""
from typing import Protocol


class GeneratedFileLike(Protocol):
    @property
    def path(self) -> str: ...

    @property
    def contents(self) -> str: ...


class GeneratedSourcesLike(Protocol):
    @property
    def files(self) -> tuple[GeneratedFileLike, ...]: ...
