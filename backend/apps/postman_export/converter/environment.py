"""Postman environment file: the single `baseUrl` variable (design.md DD111).

The value is supplied by the caller and defaults to empty, so no host, port or
URL literal ever lives in this package (AGENTS.md rule 4). The collection only
references `{{baseUrl}}`; the value exists solely in this file.
"""
from .requests import BASE_URL_VARIABLE

_NAME_SUFFIX = "Environment"


def build_environment(document: dict, base_url: str = "") -> dict:
    """Return the environment dict named after the document title."""
    title = document.get("info", {}).get("title", "")
    return {
        "name": f"{title} {_NAME_SUFFIX}" if title else _NAME_SUFFIX,
        "values": [{"key": BASE_URL_VARIABLE, "value": base_url, "enabled": True}],
        "_postman_variable_scope": "environment",
    }
