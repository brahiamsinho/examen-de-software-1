"""Byte-identical output (spec: Pure Deterministic Converter, design.md DD112)."""
import json
from pathlib import Path

from apps.postman_export.converter import build_collection, build_environment
from apps.postman_export.converter.serialize import to_json_text, write_json

FIXTURE = Path(__file__).parent / "fixtures" / "api-docs.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {key for value in node.values() for key in _keys(value)}
    if isinstance(node, list):
        return {key for value in node for key in _keys(value)}
    return set()


def test_two_conversions_of_the_same_input_are_equal():
    assert build_collection(_fixture()) == build_collection(_fixture())
    assert build_environment(_fixture(), "value") == build_environment(_fixture(), "value")


def test_serialized_files_are_byte_identical_across_runs(tmp_path):
    first, second = tmp_path / "first.json", tmp_path / "second.json"

    write_json(first, build_collection(_fixture()))
    write_json(second, build_collection(_fixture()))

    assert first.read_bytes() == second.read_bytes()
    assert len(first.read_bytes()) > 1000


def test_no_volatile_fields_anywhere():
    collection = build_collection(_fixture())
    environment = build_environment(_fixture())

    assert "_postman_id" not in _keys(collection) | _keys(environment)
    assert "id" not in _keys(collection) | _keys(environment)


def test_output_ends_with_one_newline_and_has_no_carriage_return(tmp_path):
    target = tmp_path / "out.json"

    write_json(target, build_collection(_fixture()))
    data = target.read_bytes()

    assert data.endswith(b"}\n")
    assert not data.endswith(b"\n\n")
    assert b"\r" not in data


def test_text_is_indented_sorted_and_keeps_non_ascii_characters():
    text = to_json_text({"b": 1, "a": "café"})

    assert text == '{\n  "a": "café",\n  "b": 1\n}\n'


def test_file_uses_utf8_without_escaping(tmp_path):
    target = tmp_path / "out.json"

    write_json(target, {"name": "café"})

    assert target.read_bytes() == '{\n  "name": "café"\n}\n'.encode("utf-8")
