"""Attribute type union and multiplicity value objects.

`AttributeType` is a closed tagged union (an eight-member primitive enum,
or an `EnumerationRef`) so a class-typed attribute is structurally
impossible to express here: cross-class links are only ever a
`Relationship` (see `domain/elements.py`).
"""
from dataclasses import dataclass
from enum import StrEnum

from apps.uml_modeling.domain.ids import ElementId


class PrimitiveType(StrEnum):
    """The exactly eight primitive attribute types (Cycle 1, closed set)."""

    STRING = "String"
    TEXT = "Text"
    INTEGER = "Integer"
    LONG = "Long"
    DECIMAL = "Decimal"
    BOOLEAN = "Boolean"
    DATE = "Date"
    DATETIME = "DateTime"


@dataclass(frozen=True)
class EnumerationRef:
    """A reference to an `Enumeration` by id, never by name."""

    enumeration_id: ElementId


AttributeType = PrimitiveType | EnumerationRef


@dataclass(frozen=True)
class Multiplicity:
    """A relationship endpoint's multiplicity range.

    Deliberately unvalidated (DD2): construction never rejects an
    out-of-range value (negative `lower`, or `upper < lower`). Range
    checking belongs solely to the `INVALID_MULTIPLICITY` validation
    rule — validating here would make that rule unreachable.
    """

    lower: int
    upper: int | None


def parse_multiplicity(text: str) -> Multiplicity:
    """Parse a UML multiplicity string into a `Multiplicity`.

    Accepts the four Cycle-1 forms: `"1"`, `"0..1"`, `"0..*"`, `"1..*"`.
    Raises `ValueError` only on malformed syntax — it never validates
    the resulting range (DD2).
    """
    if ".." not in text:
        return _parse_bound(text, text)

    lower_text, _, upper_text = text.partition("..")
    return _parse_bound(lower_text, upper_text)


def _parse_bound(lower_text: str, upper_text: str) -> Multiplicity:
    try:
        lower = int(lower_text)
    except ValueError as error:
        raise ValueError(f"Malformed multiplicity: {lower_text!r}..{upper_text!r}") from error

    if upper_text == "*":
        return Multiplicity(lower, None)

    try:
        upper = int(upper_text)
    except ValueError as error:
        raise ValueError(f"Malformed multiplicity: {lower_text!r}..{upper_text!r}") from error

    return Multiplicity(lower, upper)


def format_multiplicity(value: Multiplicity) -> str:
    """Format a `Multiplicity` back into its UML string notation."""
    if value.upper is None:
        return f"{value.lower}..*"
    if value.lower == value.upper:
        return str(value.lower)
    return f"{value.lower}..{value.upper}"
