"""Mapper wiring of generation profiles (relational-mapping spec; DD141,
STI root rule, synthetic columns). Profiles are declared through
`CanonicalUmlModel.generation_metadata` and carried on `Table` / `Column`.
"""
import dataclasses

import pytest

from apps.relational_mapping.domain.profile import (
    ColumnProfile,
    CrudOperation,
    DefaultSort,
    SortDirection,
    TableProfile,
)
from apps.relational_mapping.mapping.errors import (
    InvalidGenerationProfileError,
    UnmappableModelError,
)
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.tests.factories import (
    a_class,
    a_generalization,
    a_hierarchy,
    a_model,
    an_association,
    an_attribute,
    an_enumeration,
)
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity


def _with_metadata(model, metadata):
    return dataclasses.replace(model, generation_metadata=metadata)


def _profile(**keys):
    return {"profile": keys}


def test_declared_class_profile_lands_on_the_table():
    order = a_class(name="Order")
    model = _with_metadata(
        a_model(classes=(order,)),
        {order.id: _profile(auditable=True, crud=["read"])},
    )

    table = map_to_relational(model).table_by_name("order")

    assert table.profile == TableProfile(auditable=True, crud=(CrudOperation.READ,))


def test_default_sort_with_an_unresolvable_attribute_id_is_carried_verbatim():
    order = a_class(name="Order")
    ghost = ElementId("no-such-attribute")
    model = _with_metadata(
        a_model(classes=(order,)),
        {order.id: _profile(defaultSort={"attribute": ghost, "direction": "desc"})},
    )

    table = map_to_relational(model).table_by_name("order")

    assert table.profile == TableProfile(
        default_sort=DefaultSort(attribute_id=ghost, direction=SortDirection.DESC)
    )


def test_declared_attribute_profile_lands_on_the_column():
    total = an_attribute(name="total")
    order = a_class(name="Order", attributes=(total,))
    model = _with_metadata(a_model(classes=(order,)), {total.id: _profile(searchable=True)})

    column = map_to_relational(model).table_by_name("order").column_by_name("total")

    assert column.profile == ColumnProfile(searchable=True)


def test_enum_typed_attribute_keeps_its_profile():
    status_enum = an_enumeration(name="OrderStatus")
    status = an_attribute(name="status", type=EnumerationRef(status_enum.id))
    order = a_class(name="Order", attributes=(status,))
    model = _with_metadata(
        a_model(classes=(order,), enumerations=(status_enum,)),
        {status.id: _profile(sortable=True)},
    )

    column = map_to_relational(model).table_by_name("order").column_by_name("status")

    assert column.profile == ColumnProfile(sortable=True)


def test_undeclared_class_and_attribute_have_no_profile():
    total = an_attribute(name="total")
    order = a_class(name="Order", attributes=(total,))

    table = map_to_relational(a_model(classes=(order,))).table_by_name("order")

    assert table.profile is None
    assert table.column_by_name("total").profile is None


def test_entity_false_still_produces_the_table():
    order = a_class(name="Order")
    model = _with_metadata(a_model(classes=(order,)), {order.id: _profile(entity=False)})

    table = map_to_relational(model).table_by_name("order")

    assert table is not None
    assert table.profile.entity is False


def test_sti_table_profile_comes_from_the_root_only():
    root, car, generalization = a_hierarchy()
    model = _with_metadata(
        a_model(classes=(root, car), relationships=(generalization,)),
        {root.id: _profile(auditable=True), car.id: _profile(readOnly=True)},
    )

    table = map_to_relational(model).table_by_name("vehicle")

    assert table.profile == TableProfile(auditable=True)
    assert table.profile.read_only is None


def test_subclass_only_class_entry_sets_no_table_profile():
    root, car, generalization = a_hierarchy()
    model = _with_metadata(
        a_model(classes=(root, car), relationships=(generalization,)),
        {car.id: _profile(auditable=True)},
    )

    assert map_to_relational(model).table_by_name("vehicle").profile is None


def test_malformed_subclass_class_entry_still_raises_for_the_subclass():
    root, car, generalization = a_hierarchy()
    model = _with_metadata(
        a_model(classes=(root, car), relationships=(generalization,)),
        {car.id: _profile(auditable=1)},
    )

    with pytest.raises(InvalidGenerationProfileError) as raised:
        map_to_relational(model)

    assert (raised.value.element_id, raised.value.key) == (car.id, "auditable")


def test_subclass_owned_attribute_keeps_its_profile_and_owner():
    wheels = an_attribute(name="wheels")
    root = a_class(name="Vehicle")
    car = a_class(name="Car", attributes=(wheels,))
    model = _with_metadata(
        a_model(classes=(root, car), relationships=(a_generalization(source_id=car.id, target_id=root.id),)),
        {wheels.id: _profile(searchable=True)},
    )

    column = map_to_relational(model).table_by_name("vehicle").column_by_name("wheels")

    assert column.profile == ColumnProfile(searchable=True)
    assert column.owning_class_id == car.id


def test_synthetic_columns_never_carry_a_profile():
    root = a_class(name="Vehicle", attributes=(an_attribute(name="plate"),))
    car = a_class(name="Car")
    owner = a_class(name="Owner")
    tag = a_class(name="Tag")
    relationships = (
        a_generalization(source_id=car.id, target_id=root.id),
        an_association(source_id=owner.id, target_id=root.id, target_multiplicity=Multiplicity(0, 1)),
        an_association(
            source_id=owner.id,
            target_id=tag.id,
            source_multiplicity=Multiplicity(0, None),
            target_multiplicity=Multiplicity(0, None),
        ),
    )
    metadata = {
        cls.id: _profile(auditable=True, readOnly=True) for cls in (root, car, owner, tag)
    }
    model = _with_metadata(
        a_model(classes=(root, car, owner, tag), relationships=relationships), metadata
    )

    relational = map_to_relational(model)

    synthetic = [
        column
        for table in relational.tables
        for column in table.columns
        if column.source_element_id is None
    ]
    names = {column.name for column in synthetic}
    assert {"id", "class_type"} <= names
    assert any(table.foreign_keys for table in relational.tables)
    assert len(relational.tables) == 4  # vehicle, owner, tag + join table
    assert all(column.profile is None for column in synthetic)
    join_table = next(t for t in relational.tables if not t.source_class_ids)
    assert join_table.profile is None


def test_unknown_ids_and_malformed_keys_outside_profile_never_raise():
    order = a_class(name="Order")
    model = _with_metadata(
        a_model(classes=(order,)),
        {
            ElementId("no-such-element"): "garbage",
            order.id: {"source": "llm", "confidence": "high", "aliases": 7, "profile": {"auditable": True}},
        },
    )

    table = map_to_relational(model).table_by_name("order")

    assert table.profile == TableProfile(auditable=True)


def test_malformed_attribute_profile_aborts_before_any_result():
    total = an_attribute(name="total")
    order = a_class(name="Order", attributes=(total,))
    model = _with_metadata(a_model(classes=(order,)), {total.id: _profile(searchable="yes")})

    with pytest.raises(UnmappableModelError) as raised:
        map_to_relational(model)

    assert isinstance(raised.value, InvalidGenerationProfileError)
    assert (raised.value.element_id, raised.value.key) == (total.id, "searchable")


def test_first_offending_entry_in_metadata_order_is_the_one_reported():
    first = a_class(name="First")
    second = a_class(name="Second")
    model = _with_metadata(
        a_model(classes=(first, second)),
        {first.id: _profile(auditable=1), second.id: _profile(readOnly="no")},
    )

    messages = []
    for _ in range(2):
        with pytest.raises(InvalidGenerationProfileError) as raised:
            map_to_relational(model)
        messages.append(str(raised.value))

    assert messages[0] == messages[1]
    assert f"element {first.id!r}" in messages[0]
