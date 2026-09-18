"""Relational column types and FK referential actions (design.md
Interfaces / Contracts). Zero framework imports: no Django, DB driver,
or Java/Spring Boot code (relational-mapping spec, Requirement:
RelationalModel Domain Structure).
"""
from enum import StrEnum


class ColumnType(StrEnum):
    UUID = "UUID"
    VARCHAR = "VARCHAR"
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    NUMERIC = "NUMERIC"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIMESTAMPTZ = "TIMESTAMPTZ"
    ENUM = "ENUM"


class ReferentialAction(StrEnum):
    NO_ACTION = "NO ACTION"
    CASCADE = "CASCADE"
    SET_NULL = "SET NULL"
    RESTRICT = "RESTRICT"
