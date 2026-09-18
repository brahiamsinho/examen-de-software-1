"""RED: apps.spring_generator.domain.sources does not exist yet.

Covers: frozen-dataclass shapes (design.md DD4), `as_mapping()`
insertion order, `file_by_path()`, and mutation raises.
"""
import dataclasses

import pytest

from apps.spring_generator.domain.sources import GeneratedFile, GeneratedSources


def test_generated_file_is_frozen():
    generated_file = GeneratedFile(path="src/main/java/com/modelia/Order.java", contents="class Order {}")

    with pytest.raises(dataclasses.FrozenInstanceError):
        generated_file.path = "other.java"


def test_generated_sources_defaults_to_empty():
    sources = GeneratedSources()

    assert sources.files == ()
    assert sources.as_mapping() == {}


def test_generated_sources_as_mapping_preserves_insertion_order():
    entity_file = GeneratedFile(path="domain/Order.java", contents="entity")
    repository_file = GeneratedFile(path="persistence/OrderRepository.java", contents="repository")
    sources = GeneratedSources(files=(entity_file, repository_file))

    mapping = sources.as_mapping()

    assert list(mapping.items()) == [
        ("domain/Order.java", "entity"),
        ("persistence/OrderRepository.java", "repository"),
    ]


def test_generated_sources_file_by_path_finds_existing_file():
    entity_file = GeneratedFile(path="domain/Order.java", contents="entity")
    sources = GeneratedSources(files=(entity_file,))

    assert sources.file_by_path("domain/Order.java") is entity_file
    assert sources.file_by_path("missing.java") is None


def test_generated_sources_is_frozen():
    sources = GeneratedSources()

    with pytest.raises(dataclasses.FrozenInstanceError):
        sources.files = ()
