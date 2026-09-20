"""Postman environment file (spec: Environment File)."""
import json
from pathlib import Path

from apps.postman_export.converter.collection import build_collection
from apps.postman_export.converter.environment import build_environment

FIXTURE = Path(__file__).parent / "fixtures" / "api-docs.json"
SENTINEL_BASE_URL = "sentinel-base-url-value"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_base_url_is_the_only_variable_and_is_empty_by_default():
    environment = build_environment({"info": {"title": "T"}})

    assert environment["values"] == [{"key": "baseUrl", "value": "", "enabled": True}]
    assert environment["_postman_variable_scope"] == "environment"


def test_base_url_carries_the_supplied_value():
    environment = build_environment({"info": {"title": "T"}}, SENTINEL_BASE_URL)

    assert environment["values"] == [{"key": "baseUrl", "value": SENTINEL_BASE_URL, "enabled": True}]


def test_name_follows_the_document_title_and_a_missing_title_stays_usable():
    assert build_environment({"info": {"title": "Shop API"}})["name"] == "Shop API Environment"
    assert build_environment({})["name"] == "Environment"


def test_no_generated_id_is_emitted():
    environment = build_environment(_fixture(), SENTINEL_BASE_URL)

    assert "id" not in environment
    assert "_postman_id" not in environment


def test_the_collection_never_carries_the_base_url_value():
    document = _fixture()
    collection_text = json.dumps(build_collection(document))
    environment_text = json.dumps(build_environment(document, SENTINEL_BASE_URL))

    assert SENTINEL_BASE_URL in environment_text
    assert SENTINEL_BASE_URL not in collection_text
    assert "variable" not in build_collection(document)
