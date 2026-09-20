"""Filesystem writer for generated sources (design.md DD78).

Pure function of its arguments: no Django, no `apps.spring_generator` import
(DD75), no container path (DD84).
"""
import re
from collections.abc import Iterable
from pathlib import Path

from apps.generation_runner.domain.errors import (
    DuplicateGeneratedPathError,
    EscapingGeneratedPathError,
    InvalidGeneratedPathError,
    NonEmptyTargetDirectoryError,
)
from apps.generation_runner.domain.protocols import GeneratedFileLike, GeneratedSourcesLike

_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
_FORBIDDEN_SEGMENTS = frozenset({"", ".", ".."})


def _resolve(path: Path) -> Path:
    """The single filesystem-resolving step; a seam for the escape-check tests."""
    return path.resolve()


def _require_empty_target(target: Path) -> None:
    """Step 1: a non-empty target could hide stale files behind a false green."""
    if target.exists() and any(target.iterdir()):
        raise NonEmptyTargetDirectoryError(str(target))


def _require_safe_path_shape(path: object) -> None:
    """Step 2: pure string checks, no filesystem access."""
    if not isinstance(path, str) or not path:
        raise InvalidGeneratedPathError(str(path), "path must be a non-empty string")
    if "\x00" in path:
        raise InvalidGeneratedPathError(path, "contains a NUL character")
    if "\\" in path:
        raise InvalidGeneratedPathError(path, "contains a backslash")
    if path.startswith("/") or _DRIVE_PREFIX.match(path):
        raise InvalidGeneratedPathError(path, "is absolute")
    if path.endswith("/"):
        raise InvalidGeneratedPathError(path, "has a trailing slash")
    if any(segment in _FORBIDDEN_SEGMENTS for segment in path.split("/")):
        raise InvalidGeneratedPathError(path, "contains an empty, '.' or '..' segment")


def _reject_duplicate_paths(paths: Iterable[str]) -> None:
    """Step 3: exact and case-insensitive repeats (a case-insensitive volume would overwrite)."""
    first_seen_by_folded_path: dict[str, str] = {}
    for path in paths:
        folded = path.casefold()
        if folded not in first_seen_by_folded_path:
            first_seen_by_folded_path[folded] = path
            continue
        previous = first_seen_by_folded_path[folded]
        if previous == path:
            raise DuplicateGeneratedPathError(path, "appears more than once")
        raise DuplicateGeneratedPathError(path, "differs only by case from {!r}".format(previous))


def _reject_escaping_paths(target: Path, relative_paths: Iterable[str]) -> None:
    """Step 4: defence in depth; shape checks cannot see a symlink, resolving can."""
    resolved_target = _resolve(target)
    for relative_path in relative_paths:
        candidate = _resolve(resolved_target / relative_path)
        if not candidate.is_relative_to(resolved_target):
            raise EscapingGeneratedPathError(relative_path, str(resolved_target))


def _write_files(target: Path, files: Iterable[GeneratedFileLike]) -> tuple[Path, ...]:
    """Step 5: the only step that touches the disk."""
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for generated_file in files:
        destination = target / generated_file.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(generated_file.contents, encoding="utf-8", newline="\n")
        written.append(destination)
    return tuple(written)


def write_sources(sources: GeneratedSourcesLike, target_dir: Path | str) -> tuple[Path, ...]:
    """Materialize `sources` under `target_dir` and return the absolute paths written.

    Validation is completed for every file before anything is created, in a
    fixed order (first failure wins): target emptiness, per-file shape,
    duplicates, resolved escape, then the write. A validation failure can
    therefore never leave a partial tree.

    Accepted limitation: an `OSError` raised in the middle of the final write
    step (disk full, permissions) is NOT rolled back. The harness clears the
    target before generating and step 1 refuses a dirty one, so a partial tree
    from a crashed run cannot silently feed a later run.
    """
    target = _resolve(Path(target_dir))
    _require_empty_target(target)

    files = tuple(sources.files)
    for generated_file in files:
        _require_safe_path_shape(generated_file.path)

    paths = tuple(generated_file.path for generated_file in files)
    _reject_duplicate_paths(paths)
    _reject_escaping_paths(target, paths)

    return _write_files(target, files)
