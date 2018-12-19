from .sys_queries import (
    all_table_functions,
    all_scalar_functions,
    all_procedures,
    all_tables,
    all_triggers,
    all_views)
import datetime
from .common_classes import Original
from dataclasses import dataclass


class DBOriginal(Original):

    @classmethod
    def key_field(cls):
        return "name"


@dataclass
class OriginalDatabase(DBOriginal):
    name: str
    last_update: datetime.datetime

@dataclass
class OriginalTable(DBOriginal):
    database_object_id: int
    schema: str
    name: str
    last_update: datetime.datetime


@dataclass
class OriginalTrigger(DBOriginal):
    database_object_id: int
    schema: str
    name: str
    last_update: datetime.datetime
    table_id: int
    is_update: bool
    is_delete: bool
    is_insert: bool
    sql: str


@dataclass
class OriginalProcedure(DBOriginal):
    database_object_id: int
    schema: str
    name: str
    last_update: datetime.datetime
    sql: str


@dataclass
class OriginalView(DBOriginal):
    database_object_id: int
    schema: str
    name: str
    last_update: datetime.datetime
    sql: str


@dataclass
class OriginalTableFunction(DBOriginal):
    database_object_id: int
    schema: str
    name: str
    last_update: datetime.datetime
    sql: str


@dataclass
class OriginalScalarFunction(DBOriginal):
    database_object_id: int
    schema: str
    name: str
    last_update: datetime.datetime
    sql: str
