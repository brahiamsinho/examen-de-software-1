"""Deterministic, dependency-free naming helpers (design.md DD4, DD8).

No English pluralization library: irregular plurals are a correctness
trap, and singular table/column names are deterministic and reversible.
"""
import re
import unicodedata

from apps.relational_mapping.mapping.errors import InvalidElementNameError

_BOUNDARY_LOWER_OR_DIGIT_THEN_UPPER = re.compile(r"([a-z0-9])([A-Z])")
_BOUNDARY_ANY_THEN_UPPER_RUN = re.compile(r"(.)([A-Z][a-z]+)")
_COMBINING_MARKS = re.compile(r"[̀-ͯ]")
_NON_ALNUM_RUN = re.compile(r"[^A-Za-z0-9]+")
_ONLY_IDENTIFIER_CHARS = re.compile(r"^[A-Za-z0-9_]*$")
_LEADING_DIGIT = re.compile(r"^[0-9]")


def snake_case(name: str) -> str:
    """CamelCase/PascalCase -> snake_case (DD4). E.g. `"OrderLine"` ->
    `"order_line"`. Never pluralizes.

    Names typed in the diagram may hold characters that are not legal in
    a DB identifier: accents are stripped (`"Órden"` -> `"orden"`), every
    other run of non-alphanumerics becomes one `_` (`"Class B"` ->
    `"class_b"`), edge underscores are trimmed and a leading digit gets an
    `n_` prefix. A name that already uses only `[A-Za-z0-9_]` is converted
    exactly as before. The UML model itself is never modified.
    """
    unaccented = _COMBINING_MARKS.sub("", unicodedata.normalize("NFKD", name))
    step1 = _BOUNDARY_ANY_THEN_UPPER_RUN.sub(r"\1_\2", unaccented)
    step2 = _BOUNDARY_LOWER_OR_DIGIT_THEN_UPPER.sub(r"\1_\2", step1)
    if _ONLY_IDENTIFIER_CHARS.match(step2):
        return step2.lower()

    cleaned = _NON_ALNUM_RUN.sub("_", step2).strip("_")
    if not cleaned:
        raise InvalidElementNameError(name)
    if _LEADING_DIGIT.match(cleaned):
        cleaned = f"n_{cleaned}"
    return cleaned.lower()


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
