"""Assemble the Postman Collection v2.1.0 from an OpenAPI document (design.md DD111, DD112, DD115).

Deterministic by construction: folders are sorted by tag, items by
(path, method), and nothing volatile (ids, timestamps) is ever emitted. No
`auth` block and no variable-setting script: one status test per request.
"""
from .requests import build_item

POSTMAN_SCHEMA_URL = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
DEFAULT_FOLDER = "default"
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")

_SUCCESS_RANGE = range(200, 300)


def build_collection(document: dict) -> dict:
    """Return the collection dict for `document` (an OpenAPI 3 mapping with `paths`)."""
    folders: dict[str, list[tuple[str, str, dict]]] = {}
    for path, path_item in document.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            item = build_item(path, method, operation, document)
            code = _lowest_success_code(operation)
            if code is not None:
                item["event"] = [_status_event(code)]
            tags = operation.get("tags") or [DEFAULT_FOLDER]
            folders.setdefault(tags[0], []).append((path, method.upper(), item))

    return {
        "info": {"name": document.get("info", {}).get("title", ""), "schema": POSTMAN_SCHEMA_URL},
        "item": [
            {"name": tag, "item": [item for _, _, item in sorted(folders[tag], key=lambda entry: entry[:2])]}
            for tag in sorted(folders)
        ],
    }


def _lowest_success_code(operation: dict) -> int | None:
    codes = [int(code) for code in operation.get("responses", {}) if code.isdigit() and int(code) in _SUCCESS_RANGE]
    return min(codes) if codes else None


def _status_event(code: int) -> dict:
    return {
        "listen": "test",
        "script": {
            "type": "text/javascript",
            "exec": [
                f'pm.test("status is {code}", function () {{',
                f"    pm.response.to.have.status({code});",
                "});",
            ],
        },
    }
