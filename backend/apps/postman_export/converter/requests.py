"""One OpenAPI operation to one Postman request item (design.md DD110-DD112, DD116).

The URL is the `{{baseUrl}}` variable plus the path: the document's `servers`
array is ignored on purpose, so no host, port or scheme enters the output and
the target is chosen in the environment file. Names are `METHOD path`, never
`operationId` (springdoc numbers duplicates, e.g. `findById_4`).
"""
import json
import re

from .examples import example_for, resolve_schema
from .serialize import dump_json

BASE_URL_VARIABLE = "baseUrl"
# Spring Data's default page size; the document only states `size` minimum 1.
DEFAULT_PAGE_SIZE = 20
JSON_MEDIA_TYPE = "application/json"

_PATH_VARIABLE = re.compile(r"\{([^}]+)\}")
_PAGEABLE_PARAMETER = "pageable"
_PAGEABLE_DEFAULTS = {"page": "0", "size": str(DEFAULT_PAGE_SIZE)}


def build_item(path: str, method: str, operation: dict, document: dict) -> dict:
    """Return the Postman item (`name` + `request`) for one operation; tests are added by the caller."""
    parameters = [resolve_schema(parameter, document) for parameter in operation.get("parameters", [])]
    query = _query_entries(parameters, document)
    headers: list[dict] = []
    request: dict = {"method": method.upper(), "header": headers, "url": _url(path, parameters, query, document)}

    body_schema = _json_body_schema(operation, document)
    if body_schema is not None:
        headers.append({"key": "Content-Type", "value": JSON_MEDIA_TYPE})
        request["body"] = {
            "mode": "raw",
            "raw": dump_json(example_for(body_schema, document)),
            "options": {"raw": {"language": "json"}},
        }
    return {"name": f"{method.upper()} {path}", "request": request}


def _url(path: str, parameters: list[dict], query: list[dict], document: dict) -> dict:
    colon_path = _PATH_VARIABLE.sub(lambda match: ":" + match.group(1), path)
    raw = "{{" + BASE_URL_VARIABLE + "}}" + colon_path
    enabled = [f"{entry['key']}={entry['value']}" for entry in query if not entry.get("disabled")]
    if enabled:
        raw += "?" + "&".join(enabled)

    url: dict = {
        "raw": raw,
        "host": ["{{" + BASE_URL_VARIABLE + "}}"],
        "path": [segment for segment in colon_path.split("/") if segment],
    }
    variables = _path_variables(path, parameters, document)
    if variables:
        url["variable"] = variables
    if query:
        url["query"] = query
    return url


def _path_variables(path: str, parameters: list[dict], document: dict) -> list[dict]:
    schemas = {p["name"]: p.get("schema", {}) for p in parameters if p.get("in") == "path"}
    variables = []
    for name in _PATH_VARIABLE.findall(path):
        example = example_for(schemas.get(name, {}), document)
        variables.append({"key": name, "value": "" if example is None else str(example)})
    return variables


def _query_entries(parameters: list[dict], document: dict) -> list[dict]:
    entries: list[dict] = []
    for parameter in parameters:
        if parameter.get("in") != "query":
            continue
        schema = resolve_schema(parameter.get("schema", {}), document)
        if parameter.get("name") == _PAGEABLE_PARAMETER and schema.get("type") == "object":
            entries.extend(_pageable_entries(schema))
        else:
            entries.append({"key": parameter["name"], "value": _query_value(example_for(schema, document))})
    return entries


def _pageable_entries(pageable_schema: dict) -> list[dict]:
    entries = []
    for name in sorted(pageable_schema.get("properties", {})):
        if name in _PAGEABLE_DEFAULTS:
            entries.append({"key": name, "value": _PAGEABLE_DEFAULTS[name]})
        else:
            entries.append({"key": name, "value": "", "disabled": True})
    return entries


def _query_value(example: object) -> str:
    if example is None:
        return ""
    return example if isinstance(example, str) else json.dumps(example)


def _json_body_schema(operation: dict, document: dict) -> dict | None:
    request_body = resolve_schema(operation.get("requestBody", {}), document)
    media = request_body.get("content", {}).get(JSON_MEDIA_TYPE)
    return None if media is None else media.get("schema", {})
