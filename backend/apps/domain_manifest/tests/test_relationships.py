"""Relationship derivation (spec: Entity Content, DD123/DD125)."""
import pytest
from apps.domain_manifest.builder.relationships import build_relationships
from apps.generation_runner.samples.sample_model import build_sample_relational_model
from apps.relational_mapping.domain.schema import Column, ForeignKey, PrimaryKey, Table, UniqueConstraint
from apps.relational_mapping.domain.types import ColumnType


def _relationship(field, attribute, column, kind, target, required=True):
    return {"field": field, "attribute": attribute, "column": column, "kind": kind, "target": target, "required": required}


def _profile_table(*unique_column_sets, nullable=False):
    return Table(
        name="profile",
        columns=(Column("id", ColumnType.UUID), Column("user_id", ColumnType.UUID, nullable=nullable)),
        primary_key=PrimaryKey(("id",)),
        foreign_keys=(ForeignKey("fk_profile__user_id", ("user_id",), "app_user", ("id",)),),
        unique_constraints=tuple(UniqueConstraint(f"uq_{index}", columns) for index, columns in enumerate(unique_column_sets)),
    )


@pytest.mark.parametrize(
    ("table", "expected"),
    [
        ("customer", []),
        ("purchase", [_relationship("customer", "customerId", "customer_id", "manyToOne", "Customer")]),
        (
            "product_tag",
            [
                _relationship("product", "productId", "product_id", "manyToOne", "Product"),
                _relationship("tag", "tagId", "tag_id", "manyToOne", "Tag"),
            ],
        ),
    ],
)
def test_sample_relationships(table, expected):
    assert build_relationships(build_sample_relational_model().table_by_name(table)) == expected


@pytest.mark.parametrize(
    ("table", "kind", "required"),
    [
        (_profile_table(("user_id",)), "oneToOne", True),
        (_profile_table(("user_id", "id")), "manyToOne", True),
        (_profile_table(), "manyToOne", True),
        (_profile_table(("user_id",), nullable=True), "oneToOne", False),
    ],
)
def test_one_to_one_only_when_a_unique_constraint_equals_the_fk_columns(table, kind, required):
    [relationship] = build_relationships(table)

    assert (relationship["kind"], relationship["required"]) == (kind, required)
    assert (relationship["field"], relationship["attribute"], relationship["target"]) == ("user", "userId", "AppUser")
