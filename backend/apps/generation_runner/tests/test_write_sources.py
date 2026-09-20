"""Behavior of `write_sources` and its typed errors (design.md DD77, DD78)."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.generation_runner.domain.errors import (
    DuplicateGeneratedPathError,
    EscapingGeneratedPathError,
    GeneratedSourceWriteError,
    InvalidGeneratedPathError,
    NonEmptyTargetDirectoryError,
)
from apps.generation_runner.writer import filesystem
from apps.generation_runner.writer.filesystem import write_sources


def _stub_sources(*entries: tuple[str, str]):
    """Plain stub objects satisfying the Protocol: no generator import."""
    return SimpleNamespace(files=tuple(SimpleNamespace(path=path, contents=contents) for path, contents in entries))


def _snapshot(directory: Path) -> list[str]:
    return sorted(str(p.relative_to(directory)) for p in directory.rglob("*"))


# --- Error hierarchy (DD77) -------------------------------------------------


def test_every_write_error_derives_from_the_shared_base():
    for error_class in (
        InvalidGeneratedPathError,
        DuplicateGeneratedPathError,
        EscapingGeneratedPathError,
        NonEmptyTargetDirectoryError,
    ):
        assert issubclass(error_class, GeneratedSourceWriteError)

    assert issubclass(GeneratedSourceWriteError, Exception)


def test_invalid_path_error_carries_path_and_reason():
    error = InvalidGeneratedPathError("a/../x", "contains a '..' segment")

    assert error.path == "a/../x"
    assert error.reason == "contains a '..' segment"
    assert "a/../x" in str(error)
    assert "contains a '..' segment" in str(error)


def test_duplicate_path_error_carries_path_and_reason():
    error = DuplicateGeneratedPathError("a/foo.java", "differs only by case from 'A/Foo.java'")

    assert error.path == "a/foo.java"
    assert error.reason == "differs only by case from 'A/Foo.java'"
    assert "differs only by case" in str(error)


def test_escaping_path_error_carries_path_and_target():
    error = EscapingGeneratedPathError("link/x", "/tmp/out")

    assert error.path == "link/x"
    assert error.target == "/tmp/out"
    assert "link/x" in str(error)
    assert "/tmp/out" in str(error)


def test_non_empty_target_error_carries_target():
    error = NonEmptyTargetDirectoryError("/tmp/out")

    assert error.target == "/tmp/out"
    assert "/tmp/out" in str(error)
    assert str(error)


def test_base_error_is_catchable_for_every_subclass():
    with pytest.raises(GeneratedSourceWriteError):
        raise NonEmptyTargetDirectoryError("/tmp/out")


# --- 2.1 shape rejections -----------------------------------------------------

SHAPE_REJECTIONS = [
    pytest.param("", id="empty"),
    pytest.param("a\x00b", id="nul"),
    pytest.param("a\\b.java", id="backslash"),
    pytest.param("/abs", id="absolute-posix"),
    pytest.param("C:\\x", id="windows-drive-backslash"),
    pytest.param("C:/x", id="windows-drive-slash"),
    pytest.param("dir/", id="trailing-slash"),
    pytest.param(".", id="dot"),
    pytest.param("..", id="dotdot"),
    pytest.param("a//b", id="empty-segment"),
    pytest.param("a/../../x", id="traversal"),
    pytest.param("a/./b", id="dot-segment"),
    pytest.param(None, id="not-a-string"),
]


@pytest.mark.parametrize("bad_path", SHAPE_REJECTIONS)
def test_unsafe_path_shapes_are_rejected_and_nothing_is_written(tmp_path, bad_path):
    sources = _stub_sources(("ok/Fine.java", "class Fine {}"), (bad_path, "x"))

    with pytest.raises(InvalidGeneratedPathError) as raised:
        write_sources(sources, tmp_path)

    assert raised.value.reason
    assert list(tmp_path.iterdir()) == []


def test_a_well_formed_relative_path_is_accepted(tmp_path):
    # Triangulation: the same call shape with only safe paths must succeed.
    written = write_sources(_stub_sources(("ok/Fine.java", "class Fine {}")), tmp_path)

    assert len(written) == 1
    assert (tmp_path / "ok" / "Fine.java").read_text(encoding="utf-8") == "class Fine {}"


# --- 2.2 duplicates -----------------------------------------------------------


def test_exact_duplicate_path_is_rejected_and_nothing_is_written(tmp_path):
    sources = _stub_sources(("A/Foo.java", "one"), ("B/Bar.java", "two"), ("A/Foo.java", "three"))

    with pytest.raises(DuplicateGeneratedPathError) as raised:
        write_sources(sources, tmp_path)

    assert raised.value.path == "A/Foo.java"
    assert list(tmp_path.iterdir()) == []


def test_case_only_duplicate_is_rejected_with_an_explanatory_message(tmp_path):
    sources = _stub_sources(("A/Foo.java", "one"), ("a/foo.java", "two"))

    with pytest.raises(DuplicateGeneratedPathError) as raised:
        write_sources(sources, tmp_path)

    assert "differs only by case" in str(raised.value)
    assert list(tmp_path.iterdir()) == []


def test_shape_errors_win_over_duplicates_regardless_of_position(tmp_path):
    # The duplicate pair precedes the bad path: duplicates are only checked
    # after every shape check has passed (DD78 step order).
    sources = _stub_sources(("A.java", "1"), ("A.java", "2"), ("../bad", "3"))

    with pytest.raises(InvalidGeneratedPathError):
        write_sources(sources, tmp_path)

    assert list(tmp_path.iterdir()) == []


# --- 2.3 target rules ---------------------------------------------------------


def test_non_empty_target_is_refused_and_stale_file_is_untouched(tmp_path):
    stale = tmp_path / "Old.java"
    stale.write_text("stale", encoding="utf-8")

    with pytest.raises(NonEmptyTargetDirectoryError) as raised:
        write_sources(_stub_sources(("New.java", "new")), tmp_path)

    assert raised.value.target == str(tmp_path.resolve())
    assert _snapshot(tmp_path) == ["Old.java"]
    assert stale.read_text(encoding="utf-8") == "stale"


def test_missing_target_is_created_on_success(tmp_path):
    target = tmp_path / "not" / "yet"

    written = write_sources(_stub_sources(("New.java", "new")), target)

    assert written == (target.resolve() / "New.java",)
    assert (target / "New.java").read_text(encoding="utf-8") == "new"


def test_empty_target_is_accepted(tmp_path):
    target = tmp_path / "empty"
    target.mkdir()

    write_sources(_stub_sources(("New.java", "new")), target)

    assert _snapshot(target) == ["New.java"]


def test_non_empty_target_wins_over_an_invalid_path(tmp_path):
    (tmp_path / "Old.java").write_text("stale", encoding="utf-8")

    with pytest.raises(NonEmptyTargetDirectoryError):
        write_sources(_stub_sources(("../bad", "x")), tmp_path)


# --- 2.4 atomicity ------------------------------------------------------------


def test_invalid_last_file_leaves_the_target_empty(tmp_path):
    entries = [(f"pkg/File{index}.java", "class X {}") for index in range(9)]
    entries.append(("pkg/../../escape.java", "boom"))

    with pytest.raises(InvalidGeneratedPathError):
        write_sources(_stub_sources(*entries), tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_missing_target_is_not_created_when_validation_fails(tmp_path):
    target = tmp_path / "never-created"

    with pytest.raises(InvalidGeneratedPathError):
        write_sources(_stub_sources(("ok.java", "x"), ("/abs", "y")), target)

    assert not target.exists()


# --- 2.5 happy path -----------------------------------------------------------


def test_contents_are_utf8_with_lf_only_and_paths_are_returned_in_input_order(tmp_path):
    sources = _stub_sources(
        ("src/main/java/com/x/Zed.java", "// caf\u00e9\nclass Zed {}\n"),
        ("build.gradle", "plugins {}\n"),
        ("src/main/resources/application.yml", "a: 1\n"),
    )

    written = write_sources(sources, str(tmp_path))

    base = tmp_path.resolve()
    assert written == (
        base / "src/main/java/com/x/Zed.java",
        base / "build.gradle",
        base / "src/main/resources/application.yml",
    )
    assert all(path.is_absolute() for path in written)

    zed_bytes = written[0].read_bytes()
    assert zed_bytes == "// caf\u00e9\nclass Zed {}\n".encode("utf-8")
    assert "\u00e9".encode("utf-8") in zed_bytes
    assert b"\r" not in zed_bytes
    assert (tmp_path / "src/main/resources").is_dir()


def test_a_bare_newline_in_contents_stays_a_single_lf_byte(tmp_path):
    # newline="\n" disables platform translation: "\n" must never become "\r\n".
    written = write_sources(_stub_sources(("a.txt", "x\ny")), tmp_path)

    assert written[0].read_bytes() == b"x\ny"


# --- 2.6 resolved-escape check (DD78 step 4) ----------------------------------
# Design gap (recorded for task 6.6): step 1 refuses any non-empty target, so a
# real pre-existing symlink can never be reached through `write_sources`. The
# escape helper is therefore tested directly with a real symlink, and the wiring
# is tested end-to-end by monkeypatching the resolve step.


def test_escape_helper_rejects_a_path_through_a_symlinked_directory(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(EscapingGeneratedPathError) as raised:
        filesystem._reject_escaping_paths(target, ("link/Evil.java",))

    assert raised.value.path == "link/Evil.java"
    assert raised.value.target == str(target.resolve())
    assert list(outside.iterdir()) == []


def test_escape_helper_accepts_paths_that_stay_inside_the_target(tmp_path):
    (tmp_path / "real").mkdir()

    # Returns None without raising: the paths resolve inside the target.
    assert filesystem._reject_escaping_paths(tmp_path, ("real/Fine.java", "new/Deep/Fine.java")) is None


def test_write_sources_runs_the_escape_check_before_writing_anything(tmp_path, monkeypatch):
    target = tmp_path / "out"
    outside = tmp_path / "outside"
    real_resolve = filesystem._resolve

    def fake_resolve(path: Path) -> Path:
        if path.name == "Evil.java":
            return outside / "Evil.java"
        return real_resolve(path)

    monkeypatch.setattr(filesystem, "_resolve", fake_resolve)
    sources = _stub_sources(("Fine.java", "ok"), ("sub/Evil.java", "boom"))

    with pytest.raises(EscapingGeneratedPathError) as raised:
        write_sources(sources, target)

    assert raised.value.path == "sub/Evil.java"
    assert not target.exists()
    assert not outside.exists()
