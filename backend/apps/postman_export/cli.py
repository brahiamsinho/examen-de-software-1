"""Command line entry point: OpenAPI document in, Postman files out (design.md DD109, DD111).

    python -m apps.postman_export.cli --openapi <file> --out-dir <dir> [--base-url <value>]

Deliberately a plain `__main__` module: no `django.setup()` and no
`DJANGO_SETTINGS_MODULE`, because `config.settings` reads `POSTGRES_*` without
defaults and the one-shot compose service has no `env_file`. Every path arrives
as an argument; no container path lives in this module.

Exit codes: 0 success; 1 unreadable file, invalid JSON, a document without
`paths`, or an unwritable output directory (message on stderr, no traceback);
2 usage error (argparse).
"""
import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from apps.postman_export.converter import build_collection, build_environment
from apps.postman_export.converter.serialize import write_json

COLLECTION_FILENAME = "postman_collection.json"
ENVIRONMENT_FILENAME = "postman_environment.json"


class _InputError(ValueError):
    """The OpenAPI input cannot be converted."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m apps.postman_export.cli",
        description="Convert an OpenAPI 3 document into a Postman collection and environment.",
    )
    parser.add_argument("--openapi", required=True, help="path of the OpenAPI JSON document")
    parser.add_argument("--out-dir", required=True, help="directory for the two Postman files (created if missing)")
    parser.add_argument("--base-url", default="", help="value of the baseUrl variable in the environment file")
    return parser


def _load_document(path: str) -> dict:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise _InputError(f"{path} is not valid JSON: {error}") from error
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        raise _InputError(f"{path} has no OpenAPI paths object")
    return document


def _convert(document: dict, base_url: str) -> tuple[dict, dict]:
    try:
        return build_collection(document), build_environment(document, base_url)
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise _InputError(f"cannot convert the document ({type(error).__name__}: {error})") from error


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)

    try:
        document = _load_document(arguments.openapi)
        collection, environment = _convert(document, arguments.base_url)
        out_dir = Path(arguments.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / COLLECTION_FILENAME, collection)
        write_json(out_dir / ENVIRONMENT_FILENAME, environment)
    except (_InputError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"wrote {COLLECTION_FILENAME} and {ENVIRONMENT_FILENAME} to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
