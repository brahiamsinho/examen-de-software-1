"""Stable JSON serialization (design.md DD112).

`sort_keys` plus a fixed indent make the text a pure function of the payload;
`newline="\n"` keeps a Windows host from turning the trailing newline into CRLF.
"""
import json
from pathlib import Path

_INDENT = 2


def dump_json(payload: object) -> str:
    """Stable JSON text without a trailing newline (also used for request bodies)."""
    return json.dumps(payload, indent=_INDENT, sort_keys=True, ensure_ascii=False)


def to_json_text(payload: object) -> str:
    return dump_json(payload) + "\n"


def write_json(path: Path | str, payload: object) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(to_json_text(payload))
