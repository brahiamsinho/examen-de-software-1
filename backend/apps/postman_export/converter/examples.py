"""Deterministic example values from an OpenAPI schema (design.md DD110, DD112).

Pure functions over plain dicts: no randomness, no clock, no environment.
`$ref` pointers are resolved inside the given document and a depth limit keeps
self-referencing schemas from recursing forever.
"""

MAX_DEPTH = 8
REF_PREFIX = "#/"

_UUID_EXAMPLE = "00000000-0000-0000-0000-000000000000"
_DATE_TIME_EXAMPLE = "2024-01-01T00:00:00Z"
_STRING_EXAMPLE = "string"


def resolve_schema(schema: dict, document: dict) -> dict:
    """Follow `$ref` pointers (local `#/...` only) until a concrete schema is reached."""
    seen: set[str] = set()
    while "$ref" in schema:
        reference = schema["$ref"]
        if reference in seen or not reference.startswith(REF_PREFIX):
            return {}
        seen.add(reference)
        node: object = document
        for part in reference[len(REF_PREFIX):].split("/"):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        schema = node if isinstance(node, dict) else {}
    return schema


def example_for(schema: dict, document: dict) -> object:
    """Return one example value for `schema`, or None when the shape is unknown or too deep."""
    return _build(schema, document, 0)


def _build(schema: dict, document: dict, depth: int) -> object:
    schema = resolve_schema(schema, document)
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]

    schema_type = schema.get("type")
    if schema_type is None and "properties" in schema:
        schema_type = "object"

    if schema_type in ("object", "array") and depth >= MAX_DEPTH:
        return None
    if schema_type == "object":
        properties = schema.get("properties", {})
        return {name: _build(child, document, depth + 1) for name, child in properties.items()}
    if schema_type == "array":
        return [_build(schema.get("items", {}), document, depth + 1)]
    if schema_type == "string":
        return _string_example(schema.get("format"))
    if schema_type in ("integer", "number"):
        return 0
    if schema_type == "boolean":
        return False
    return None


def _string_example(string_format: str | None) -> str:
    if string_format == "uuid":
        return _UUID_EXAMPLE
    if string_format == "date-time":
        return _DATE_TIME_EXAMPLE
    return _STRING_EXAMPLE
