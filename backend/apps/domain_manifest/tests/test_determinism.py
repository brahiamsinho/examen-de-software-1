"""Deterministic ordering and serialization (spec, DD127): the file is a pure function of the model."""
import json

import pytest
from apps.domain_manifest.builder import build_manifest
from apps.domain_manifest.serialize import to_json_text, write_json
from apps.generation_runner.samples.sample_model import build_sample_relational_model

VOLATILE_KEYS = {"id", "uuid", "createdAt", "updatedAt", "generatedAt", "timestamp", "date"}


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


def _written(tmp_path, name="domain-manifest.json"):
    path = tmp_path / name
    write_json(path, build_manifest(build_sample_relational_model()))
    return path.read_bytes()


CHECKS = {
    "equal dicts": lambda tmp: build_manifest(build_sample_relational_model()) == build_manifest(build_sample_relational_model()),
    "identical bytes": lambda tmp: _written(tmp, "a.json") == _written(tmp, "b.json"),
    "one trailing newline": lambda tmp: _written(tmp).endswith(b"}\n"),
    "no carriage return": lambda tmp: b"\r" not in _written(tmp),
    "no volatile key": lambda tmp: not VOLATILE_KEYS & set(_keys(json.loads(_written(tmp)))),
    "reserialize reproduces": lambda tmp: to_json_text(json.loads(_written(tmp))).encode("utf-8") == _written(tmp),
}


@pytest.mark.parametrize("check", CHECKS.values(), ids=CHECKS.keys())
def test_determinism_check(check, tmp_path):
    assert check(tmp_path) is True


def test_serialization_is_sorted_indented_and_keeps_non_ascii(tmp_path):
    path = tmp_path / "out.json"

    write_json(path, {"b": 1, "a": "Estado é"})

    assert path.read_bytes() == '{\n  "a": "Estado é",\n  "b": 1\n}\n'.encode("utf-8")
