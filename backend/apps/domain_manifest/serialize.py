"""Stable JSON serialization (design.md DD124, DD127).

Duplicated from `postman_export` on purpose: both apps stay independently
revertible. `sort_keys` plus a fixed indent make the text a pure function of the
payload; `newline="\n"` keeps a Windows host from writing CRLF.
"""
import json
from pathlib import Path

_INDENT = 2


def to_json_text(payload: object) -> str:
    return json.dumps(payload, indent=_INDENT, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path: Path | str, payload: object) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(to_json_text(payload))
