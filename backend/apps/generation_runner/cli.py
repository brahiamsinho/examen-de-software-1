"""Command line entry point: write the sample project to a directory (design.md DD79).

    python -m apps.generation_runner.cli --target <dir> [--base-package <pkg>]

Deliberately a plain `__main__` module: no `django.setup()` and no
`DJANGO_SETTINGS_MODULE`, because `config.settings` reads `POSTGRES_*` without
defaults and the one-shot compose service has no `env_file`. The target path
arrives only as an argument (DD84); no container path lives in this module.

Exit codes: 0 success; 1 any write error or generation error (message on
stderr, no traceback); 2 usage error (argparse).
"""
import argparse
import sys
from collections.abc import Sequence

from apps.generation_runner.domain.errors import GeneratedSourceWriteError
from apps.generation_runner.samples.sample_model import build_sample_relational_model
from apps.generation_runner.writer import write_sources
from apps.spring_generator.emit.errors import UngeneratableSourceError
from apps.spring_generator.emit.renderer import generate_project_sources

DEFAULT_BASE_PACKAGE = "com.modelia.generated"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m apps.generation_runner.cli",
        description="Generate the sample Spring Boot project into an empty directory.",
    )
    parser.add_argument("--target", required=True, help="directory to write into (must be missing or empty)")
    parser.add_argument("--base-package", default=DEFAULT_BASE_PACKAGE, help="Java base package")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)

    try:
        sources = generate_project_sources(build_sample_relational_model(), base_package=arguments.base_package)
        written = write_sources(sources, arguments.target)
    except (GeneratedSourceWriteError, UngeneratableSourceError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"wrote {len(written)} files to {arguments.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
