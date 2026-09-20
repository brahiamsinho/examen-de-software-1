"""Command line entry point: sample model in, `domain-manifest.json` out (design.md DD124, DD127).

    python -m apps.domain_manifest.cli --out-dir <dir>

Deliberately a plain `__main__` module: no `django.setup()` and no
`DJANGO_SETTINGS_MODULE`, because `config.settings` reads `POSTGRES_*` without
defaults and the one-shot compose service has no `env_file`. The manifest is
built in-process from the sample model, like `generation_runner/cli.py`.

Exit codes: 0 success; 1 an unwritable output directory or a model the builder
rejects (message on stderr, no traceback); 2 usage error (argparse).
"""
import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from apps.domain_manifest.builder import build_manifest
from apps.domain_manifest.serialize import write_json
from apps.generation_runner.samples.sample_model import build_sample_relational_model

MANIFEST_FILENAME = "domain-manifest.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m apps.domain_manifest.cli",
        description="Write the Domain Manifest of the sample model as domain-manifest.json.",
    )
    parser.add_argument("--out-dir", required=True, help="directory for domain-manifest.json (created if missing)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)

    try:
        manifest = build_manifest(build_sample_relational_model())
        out_dir = Path(arguments.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(out_dir / MANIFEST_FILENAME, manifest)
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"wrote {MANIFEST_FILENAME} to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
