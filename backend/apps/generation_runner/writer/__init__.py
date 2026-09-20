"""Pure filesystem writer package (design.md DD75): never imports `apps.spring_generator`."""
from apps.generation_runner.writer.filesystem import write_sources

__all__ = ["write_sources"]
