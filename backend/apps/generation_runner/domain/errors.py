"""Typed failures of the generated-source writer (design.md DD77).

Four failure modes, four different operator responses: fix the generator
(invalid path), fix a name collision (duplicate), treat as a security
incident (escape), clear the target (non-empty). A shared base lets the CLI
catch one type and exit non-zero. Every error carries the offending value.

Pure: no Django, no `apps.spring_generator` import (DD75).
"""


class GeneratedSourceWriteError(Exception):
    """Root for every error `write_sources` raises."""


class InvalidGeneratedPathError(GeneratedSourceWriteError):
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__("Invalid generated path {!r}: {}".format(path, reason))


class DuplicateGeneratedPathError(GeneratedSourceWriteError):
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__("Duplicate generated path {!r}: {}".format(path, reason))


class EscapingGeneratedPathError(GeneratedSourceWriteError):
    def __init__(self, path: str, target: str):
        self.path = path
        self.target = target
        super().__init__("Generated path {!r} resolves outside target directory {!r}".format(path, target))


class NonEmptyTargetDirectoryError(GeneratedSourceWriteError):
    def __init__(self, target: str):
        self.target = target
        super().__init__(
            "Target directory {!r} is not empty; refusing to write over stale files".format(target)
        )
