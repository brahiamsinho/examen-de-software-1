"""Collection conversion driven by the REAL captured `/v3/api-docs` body.

Fixture provenance (DD114): `fixtures/api-docs.json` is the byte-identical body
the gate (`scripts/verify-generated-project.sh`) received from the generated
project's springdoc 3.1.1 (OpenAPI 3.1.0) on 2026-09-20. It is NOT trimmed:
14408 bytes, all five sample controllers. Synthetic documents below only cover
shapes the sample project cannot produce (untagged operations, several 2xx
codes, no 2xx at all).
"""
import ast
import json
from pathlib import Path

import apps.postman_export as export_package
from apps.postman_export.converter.collection import POSTMAN_SCHEMA_URL, build_collection

FIXTURE = Path(__file__).parent / "fixtures" / "api-docs.json"
EXPORT_ROOT = Path(export_package.__file__).resolve().parent
EXPECTED_FOLDERS = [
    "customer-controller",
    "product-controller",
    "product-tag-controller",
    "purchase-controller",
    "tag-controller",
]
EXPECTED_CUSTOMER_ITEMS = [
    "GET /api/customers",
    "POST /api/customers",
    "GET /api/customers/count",
    "DELETE /api/customers/{id}",
    "GET /api/customers/{id}",
    "PUT /api/customers/{id}",
]
CHAINING_CALLS = ("pm.environment.set", "pm.collectionVariables.set", "pm.variables.set", "pm.globals.set")


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _folder(collection: dict, name: str) -> dict:
    return next(folder for folder in collection["item"] if folder["name"] == name)


def _all_requests(collection: dict) -> list[dict]:
    return [item for folder in collection["item"] for item in folder["item"]]


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {key for value in node.values() for key in _keys(value)}
    if isinstance(node, list):
        return {key for value in node for key in _keys(value)}
    return set()


def _status_scripts(item: dict) -> list[dict]:
    return [event for event in item.get("event", []) if event["listen"] == "test"]


def test_envelope_has_the_v21_schema_the_document_title_and_no_auth():
    collection = build_collection(_fixture())

    assert collection["info"]["schema"] == "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    assert collection["info"]["name"] == "OpenAPI definition"
    assert "auth" not in _keys(collection)


def test_the_schema_url_literal_lives_in_exactly_one_place():
    occurrences = [
        path.name
        for path in sorted(EXPORT_ROOT.rglob("*.py"))
        if "tests" not in path.relative_to(EXPORT_ROOT).parts
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and node.value == POSTMAN_SCHEMA_URL
    ]

    assert occurrences == ["collection.py"]


def test_one_sorted_folder_per_controller_tag():
    collection = build_collection(_fixture())

    assert [folder["name"] for folder in collection["item"]] == EXPECTED_FOLDERS
    assert len(_all_requests(collection)) == 30


def test_items_are_sorted_by_path_then_method_and_named_method_plus_path():
    customer = _folder(build_collection(_fixture()), "customer-controller")

    assert [item["name"] for item in customer["item"]] == EXPECTED_CUSTOMER_ITEMS


def test_order_does_not_depend_on_the_input_order():
    document = _fixture()
    shuffled = dict(document)
    shuffled["paths"] = {
        path: dict(reversed(list(operations.items()))) for path, operations in reversed(list(document["paths"].items()))
    }

    assert list(shuffled["paths"]) != list(document["paths"])
    assert build_collection(shuffled) == build_collection(document)


def test_each_request_has_exactly_one_status_test_on_its_lowest_2xx_code():
    collection = build_collection(_fixture())
    expected = {"GET": 200, "PUT": 200, "POST": 201, "DELETE": 204}

    requests = _all_requests(collection)
    assert len(requests) == 30
    for item in requests:
        scripts = _status_scripts(item)
        assert len(scripts) == 1, item["name"]
        code = expected[item["request"]["method"]]
        assert scripts[0]["script"] == {
            "type": "text/javascript",
            "exec": [f'pm.test("status is {code}", function () {{', f"    pm.response.to.have.status({code});", "});"],
        }


def test_status_test_uses_the_lowest_documented_2xx_code():
    document = {
        "info": {"title": "T"},
        "paths": {
            "/a": {"post": {"responses": {"404": {}, "201": {}, "200": {}, "default": {}}}},
            "/b": {"get": {"responses": {"default": {}, "404": {}}}},
        },
    }

    items = _all_requests(build_collection(document))

    assert [item["name"] for item in items] == ["POST /a", "GET /b"]
    assert _status_scripts(items[0])[0]["script"]["exec"][1] == "    pm.response.to.have.status(200);"
    assert _status_scripts(items[1]) == []


def test_no_script_sets_variables_and_no_generated_ids_exist():
    collection = build_collection(_fixture())

    lines = [line for item in _all_requests(collection) for event in item["event"] for line in event["script"]["exec"]]
    assert lines
    assert not [line for line in lines if any(call in line for call in CHAINING_CALLS)]
    assert not {"id", "_postman_id", "prerequest"} & _keys(collection)
    assert all(event["listen"] == "test" for item in _all_requests(collection) for event in item["event"])


def test_paged_lists_expand_pageable_and_other_requests_have_no_query():
    collection = build_collection(_fixture())
    customer = {item["name"]: item for item in _folder(collection, "customer-controller")["item"]}

    paged = customer["GET /api/customers"]["request"]["url"]
    assert [entry["key"] for entry in paged["query"]] == ["page", "size", "sort"]
    assert paged["raw"] == "{{baseUrl}}/api/customers?page=0&size=20"
    assert "pageable" not in json.dumps(collection)
    assert "query" not in customer["GET /api/customers/count"]["request"]["url"]


def test_post_bodies_and_path_variables_come_from_the_real_schemas():
    customer = {item["name"]: item for item in _folder(build_collection(_fixture()), "customer-controller")["item"]}

    post = customer["POST /api/customers"]["request"]
    assert json.loads(post["body"]["raw"]) == {"fullName": "string"}
    assert customer["GET /api/customers/{id}"]["request"]["url"]["raw"] == "{{baseUrl}}/api/customers/:id"
    assert customer["GET /api/customers/{id}"]["request"]["url"]["variable"][0]["key"] == "id"


def test_untagged_operations_land_in_the_default_folder_sorted_with_the_tags():
    document = {
        "info": {"title": "T"},
        "paths": {
            "/x": {"get": {"responses": {"200": {}}}},
            "/y": {"get": {"tags": ["zeta"], "responses": {"200": {}}}},
            "/z": {"get": {"tags": ["alpha", "zeta"], "responses": {"200": {}}}},
        },
    }

    collection = build_collection(document)

    assert [folder["name"] for folder in collection["item"]] == ["alpha", "default", "zeta"]
    assert [item["name"] for item in _folder(collection, "default")["item"]] == ["GET /x"]
    assert [item["name"] for item in _folder(collection, "alpha")["item"]] == ["GET /z"]
