"""RED: apps.spring_generator.emit.naming.resource_path_segment and
apps.spring_generator.emit.errors.InvalidResourcePathError /
reject_invalid_resource_path do not exist yet.

Covers: the DD45 3-rule pluralizer, kebab-case output, illegal segment
rejection, and that the check runs after DD35's four existing checks
(design.md DD45).
"""
import pytest

from apps.relational_mapping.domain.schema import Column
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.errors import (
    InvalidResourcePathError,
    UngeneratableTableError,
    reject_invalid_resource_path,
    reject_out_of_scope,
)
from apps.spring_generator.emit.naming import resource_path_segment
from apps.spring_generator.tests.factories import a_table


@pytest.mark.parametrize(
    "table_name,expected_segment",
    [
        ("product", "products"),
        ("category", "categories"),
        ("status", "statuses"),
        ("box", "boxes"),
        ("order_line", "order-lines"),
        ("day", "days"),
    ],
)
def test_resource_path_segment_pluralizes_deterministically(table_name, expected_segment):
    assert resource_path_segment(table_name) == expected_segment


def test_resource_path_segment_never_contains_underscore_or_uppercase():
    segment = resource_path_segment("order_line")

    assert "_" not in segment
    assert segment == segment.lower()


def test_resource_path_segment_illegal_output_raises():
    with pytest.raises(InvalidResourcePathError):
        resource_path_segment("order line")


def test_reject_invalid_resource_path_raises_for_illegal_table_name():
    table = a_table(name="order line")

    with pytest.raises(InvalidResourcePathError) as excinfo:
        reject_invalid_resource_path(table)

    assert isinstance(excinfo.value, UngeneratableTableError)


def test_reject_invalid_resource_path_raises_nothing_for_legal_table_name():
    table = a_table(name="product")

    assert reject_invalid_resource_path(table) is None


def test_resource_path_check_runs_after_pk_shape_check():
    # A table with both an unsupported PK shape (DD35 step 1) and an
    # illegal name for the resource path (DD45 step 5) must fail on the
    # PK check first when both checks run in the pipeline's declared
    # order.
    from apps.relational_mapping.domain.schema import PrimaryKey
    from apps.spring_generator.emit.errors import UnsupportedPrimaryKeyError

    table = a_table(
        name="order line",
        columns=(Column(name="id", type=ColumnType.BIGINT),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_table"),
    )

    with pytest.raises(UnsupportedPrimaryKeyError):
        reject_out_of_scope(table)
        reject_invalid_resource_path(table)
