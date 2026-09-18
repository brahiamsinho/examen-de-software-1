"""Frozen, DB-free, framework-agnostic `RelationalModel` dataclasses
(spec §21). This is the sole output shape of
`mapping.mapper.map_to_relational`. Zero Django, DB driver, or
Java/Spring Boot imports (design.md DD2; relational-mapping spec,
Requirement: RelationalModel Domain Structure).
"""
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from apps.relational_mapping.domain.types import ColumnType, ReferentialAction
from apps.uml_modeling.domain.ids import ElementId

EMPTY: Mapping[ElementId, str] = MappingProxyType({})


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType
    nullable: bool = False
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    enum_type_name: str | None = None
    source_element_id: ElementId | None = None


@dataclass(frozen=True)
class PrimaryKey:
    column_names: tuple[str, ...]
    name: str | None = None


@dataclass(frozen=True)
class ForeignKey:
    name: str
    column_names: tuple[str, ...]
    referenced_table: str
    referenced_column_names: tuple[str, ...]
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION
    on_update: ReferentialAction = ReferentialAction.NO_ACTION
    source_relationship_id: ElementId | None = None


@dataclass(frozen=True)
class UniqueConstraint:
    name: str
    column_names: tuple[str, ...]


@dataclass(frozen=True)
class Index:
    name: str
    column_names: tuple[str, ...]
    unique: bool = False


@dataclass(frozen=True)
class EnumType:
    name: str
    labels: tuple[str, ...]
    source_enumeration_id: ElementId | None = None


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[Column, ...]
    primary_key: PrimaryKey
    foreign_keys: tuple[ForeignKey, ...] = ()
    unique_constraints: tuple[UniqueConstraint, ...] = ()
    indexes: tuple[Index, ...] = ()
    source_class_ids: tuple[ElementId, ...] = ()
    discriminator_column: str | None = None
    discriminator_values: Mapping[ElementId, str] = EMPTY

    def column_by_name(self, name: str) -> Column | None:
        for column in self.columns:
            if column.name == name:
                return column
        return None


@dataclass(frozen=True)
class RelationalModel:
    tables: tuple[Table, ...] = ()
    enum_types: tuple[EnumType, ...] = ()

    def table_by_name(self, name: str) -> Table | None:
        for table in self.tables:
            if table.name == name:
                return table
        return None

    def enum_type_by_name(self, name: str) -> EnumType | None:
        for enum_type in self.enum_types:
            if enum_type.name == name:
                return enum_type
        return None
