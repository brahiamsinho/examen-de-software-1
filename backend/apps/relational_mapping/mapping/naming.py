"""Deterministic, dependency-free naming helpers (design.md DD4, DD8).

No English pluralization library: irregular plurals are a correctness
trap, and singular table/column names are deterministic and reversible.
"""
import re

_BOUNDARY_LOWER_OR_DIGIT_THEN_UPPER = re.compile(r"([a-z0-9])([A-Z])")
_BOUNDARY_ANY_THEN_UPPER_RUN = re.compile(r"(.)([A-Z][a-z]+)")


def snake_case(name: str) -> str:
    """CamelCase/PascalCase -> snake_case (DD4). E.g. `"OrderLine"` ->
    `"order_line"`. Never pluralizes.
    """
    step1 = _BOUNDARY_ANY_THEN_UPPER_RUN.sub(r"\1_\2", name)
    step2 = _BOUNDARY_LOWER_OR_DIGIT_THEN_UPPER.sub(r"\1_\2", step1)
    return step2.lower()


def unique_name(taken: set[str], preferred: str, owner: str | None = None) -> str:
    """Total, deterministic collision resolution (DD8): keep `preferred`
    if free; else prefix with the owning class's `snake_case` name if
    `owner` is given and that is free; else append `_2`, `_3`, ...
    """
    if preferred not in taken:
        return preferred

    candidate = preferred
    if owner is not None:
        candidate = f"{snake_case(owner)}_{preferred}"
        if candidate not in taken:
            return candidate

    suffix = 2
    while True:
        numbered = f"{candidate}_{suffix}"
        if numbered not in taken:
            return numbered
        suffix += 1
