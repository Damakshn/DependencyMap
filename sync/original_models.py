from .sys_queries import (
    all_functions,
    all_procedures,
    all_tables,
    all_triggers,
    all_views)
from sqlalchemy import Column, Integer, String, DateTime, Table
from sqlalchemy.ext.declarative import declarative_base

OriginalBase = declarative_base()


class OriginalTable(OriginalBase):
    __tablename__ = all_tables
    database_object_id = Column(Integer, primary_key=True)
    schema_name = Column(String)
    name = Column(String)
    last_update = Column(DateTime)
"""
class OriginalTrigger(OriginalBase):
    __tablename__ = all_triggers


class OriginalProcedure(OriginalBase):
    __tablename__ = all_procedures


class OriginalView(OriginalBase):
    __tablename__ = all_views


class OriginalFunction(OriginalBase):
    __tablename__ = all_functions
"""
