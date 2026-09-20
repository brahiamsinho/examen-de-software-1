"""Operation to Postman request mapping (spec: Request URL and Naming, Pageable Expansion)."""
import json

from apps.postman_export.converter.requests import BASE_URL_VARIABLE, DEFAULT_PAGE_SIZE, build_item

DOCUMENT = {
    "servers": [{"url": "http://host.invalid:9999"}],
    "components": {
        "schemas": {
            "CustomerRequestDto": {"type": "object", "properties": {"fullName": {"type": "string"}}},
            "Pageable": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "minimum": 0},
                    "size": {"type": "integer", "minimum": 1},
                    "sort": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}
ID_PARAMETER = {"name": "id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}
PAGEABLE_PARAMETER = {
    "name": "pageable",
    "in": "query",
    "required": True,
    "schema": {"$ref": "#/components/schemas/Pageable"},
}


def _request(item: dict) -> dict:
    return item["request"]


def test_path_variable_becomes_colon_id_with_a_variable_entry():
    item = build_item("/api/customers/{id}", "get", {"operationId": "findById_4", "parameters": [ID_PARAMETER]}, DOCUMENT)

    url = _request(item)["url"]
    assert url["raw"] == "{{baseUrl}}/api/customers/:id"
    assert url["host"] == ["{{baseUrl}}"]
    assert url["path"] == ["api", "customers", ":id"]
    assert url["variable"] == [{"key": "id", "value": "00000000-0000-0000-0000-000000000000"}]


def test_path_without_parameters_has_no_variable_and_two_variables_keep_path_order():
    plain = build_item("/api/customers", "get", {}, DOCUMENT)
    nested = build_item(
        "/api/customers/{customerId}/orders/{orderId}",
        "get",
        {"parameters": [{"name": "orderId", "in": "path", "schema": {"type": "integer"}},
                        {"name": "customerId", "in": "path", "schema": {"type": "string"}}]},
        DOCUMENT,
    )

    assert "variable" not in _request(plain)["url"]
    assert _request(plain)["url"]["raw"] == "{{baseUrl}}/api/customers"
    assert [variable["key"] for variable in _request(nested)["url"]["variable"]] == ["customerId", "orderId"]
    assert _request(nested)["url"]["raw"] == "{{baseUrl}}/api/customers/:customerId/orders/:orderId"


def test_servers_are_ignored():
    item = build_item("/api/customers", "get", {}, DOCUMENT)

    assert "host.invalid" not in json.dumps(item)
    assert "9999" not in json.dumps(item)
    assert BASE_URL_VARIABLE == "baseUrl"


def test_name_is_method_plus_path_and_ignores_operation_id():
    first = build_item("/api/customers/{id}", "get", {"operationId": "same"}, DOCUMENT)
    second = build_item("/api/customers/{id}", "delete", {"operationId": "same"}, DOCUMENT)

    assert first["name"] == "GET /api/customers/{id}"
    assert second["name"] == "DELETE /api/customers/{id}"
    assert _request(first)["method"] == "GET"
    assert _request(second)["method"] == "DELETE"


def test_json_body_is_generated_only_when_there_is_a_request_body():
    operation = {
        "requestBody": {
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CustomerRequestDto"}}},
            "required": True,
        }
    }

    with_body = _request(build_item("/api/customers", "post", operation, DOCUMENT))
    without_body = _request(build_item("/api/customers", "get", {}, DOCUMENT))

    assert with_body["body"]["mode"] == "raw"
    assert with_body["body"]["options"] == {"raw": {"language": "json"}}
    assert json.loads(with_body["body"]["raw"]) == {"fullName": "string"}
    assert with_body["header"] == [{"key": "Content-Type", "value": "application/json"}]
    assert "body" not in without_body
    assert without_body["header"] == []


def test_a_non_json_request_body_produces_no_body():
    operation = {"requestBody": {"content": {"text/plain": {"schema": {"type": "string"}}}}}

    request = _request(build_item("/api/notes", "post", operation, DOCUMENT))

    assert "body" not in request
    assert request["header"] == []


def test_pageable_ref_parameter_is_expanded_into_page_size_and_sort():
    item = build_item("/api/customers", "get", {"parameters": [PAGEABLE_PARAMETER]}, DOCUMENT)

    url = _request(item)["url"]
    assert url["query"] == [
        {"key": "page", "value": "0"},
        {"key": "size", "value": str(DEFAULT_PAGE_SIZE)},
        {"key": "sort", "value": "", "disabled": True},
    ]
    assert url["raw"] == "{{baseUrl}}/api/customers?page=0&size=20"
    assert "pageable" not in json.dumps(item)


def test_other_query_parameters_are_kept_with_an_example_value():
    operation = {"parameters": [{"name": "active", "in": "query", "schema": {"type": "boolean"}}]}

    url = _request(build_item("/api/customers", "get", operation, DOCUMENT))["url"]

    assert url["query"] == [{"key": "active", "value": "false"}]
    assert url["raw"] == "{{baseUrl}}/api/customers?active=false"
