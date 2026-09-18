"""RED: mapper stage 4-5 incomplete. Property tests for the §21
determinism criterion (design.md Testing Strategy, Property row).
"""
from hypothesis import given, strategies as st

from apps.relational_mapping.domain.types import ColumnType
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import a_class, a_model, an_association, an_attribute
from apps.uml_modeling.domain.types import Multiplicity, PrimitiveType

_CLASS_NAMES = ["Order", "Customer", "OrderLine", "Product"]
_ATTRIBUTE_NAMES = ["name", "code", "amount", "description"]


@st.composite
def _uml_models(draw):
    class_count = draw(st.integers(min_value=1, max_value=4))
    names = _CLASS_NAMES[:class_count]
    classes = []
    for name in names:
        attribute_count = draw(st.integers(min_value=0, max_value=2))
        attributes = tuple(
            an_attribute(name=_ATTRIBUTE_NAMES[i], type=PrimitiveType.STRING)
            for i in range(attribute_count)
        )
        classes.append(a_class(name=name, attributes=attributes))

    relationships = []
    if len(classes) >= 2 and draw(st.booleans()):
        source_idx, target_idx = draw(
            st.tuples(
                st.integers(min_value=0, max_value=len(classes) - 1),
                st.integers(min_value=0, max_value=len(classes) - 1),
            ).filter(lambda pair: pair[0] != pair[1])
        )
        lower = draw(st.integers(min_value=0, max_value=1))
        many = draw(st.booleans())
        relationships.append(
            an_association(
                source_id=classes[source_idx].id,
                target_id=classes[target_idx].id,
                source_multiplicity=Multiplicity(lower, 1),
                target_multiplicity=Multiplicity(0, None) if many else Multiplicity(0, 1),
            )
        )

    return a_model(classes=tuple(classes), relationships=tuple(relationships))


@given(_uml_models())
def test_repeated_mapping_is_structurally_identical(model):
    assert map_to_relational(model) == map_to_relational(model)


@given(_uml_models())
def test_every_fk_referenced_table_and_column_exist(model):
    result = map_to_relational(model)
    for table in result.tables:
        for fk in table.foreign_keys:
            referenced = result.table_by_name(fk.referenced_table)
            assert referenced is not None
            for column_name in fk.referenced_column_names:
                assert referenced.column_by_name(column_name) is not None


@given(_uml_models())
def test_column_names_are_unique_within_a_table(model):
    result = map_to_relational(model)
    for table in result.tables:
        names = [column.name for column in table.columns]
        assert len(names) == len(set(names))


@given(_uml_models())
def test_every_table_has_exactly_one_single_column_uuid_pk(model):
    result = map_to_relational(model)
    for table in result.tables:
        assert len(table.primary_key.column_names) == 1
        pk_column = table.column_by_name(table.primary_key.column_names[0])
        assert pk_column is not None
        assert pk_column.type is ColumnType.UUID
