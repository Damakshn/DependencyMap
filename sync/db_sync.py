from sqlalchemy.orm import selectinload, joinedload
from .common_classes import SyncException
from dpm.models import (
    Database,
    DBTable,
    DBScalarFunction,
    DBTableFunction,
    DBView,
    DBStoredProcedure,
    DBTrigger)
import sync.sys_queries as sys_queries
import sync.original_models as original_models
from .common_functions import (
    sync_subordinate_members,
    get_remaining_objects,
    make_node_from)
from typing import List, Dict
import itertools

def to_dict(dbname: str, cls, dataset):
    """
    Превращает набор строк в словарь объектов-оригиналов
    выбранного класса;

    Ключ - база.схема.название
    """
    return {
        f"{dbname}.{row[1]}.{row[2]}":
        cls(**row) for row in dataset
    }

def sync_database(base, session, conn):
    """
    Синхронизирует одну базу данных целиком.
    """
    # проверить дату последнего изменения метаданных базы
    meta = conn.execute(sys_queries.database_metadata).first()
    original_db = original_models.OriginalDatabase(**meta)
    # если в оригинале не было изменений, выходим
    if original_db.last_update == base.last_update:
        return
    # вытаскиваем всю хранимую информацию по базе без ленивой загрузки
    base = session.query(Database).options(
        selectinload(Database.views),
        selectinload(Database.procedures),
        selectinload(Database.table_functions),
        selectinload(Database.scalar_functions),
        selectinload(Database.tables),
        selectinload(Database.triggers)).filter(Database.id == base.id).one()
    # синхронизируем по очереди все типы объектов
    # процедуры
    proc_data_set = conn.execute(sys_queries.all_procedures)
    procedures = to_dict(base.name, original_models.OriginalProcedure, proc_data_set)
    sync_subordinate_members(procedures, base.procedures, session, parent=base)
    # представления
    views_data_set = conn.execute(sys_queries.all_views)
    views = to_dict(base.name, original_models.OriginalView, views_data_set)
    sync_subordinate_members(views, base.views, session, parent=base)
    # табличные функции
    tabfunc_data_set = conn.execute(sys_queries.all_table_functions)
    tfunctions = to_dict(base.name, original_models.OriginalTableFunction, tabfunc_data_set)
    sync_subordinate_members(tfunctions, base.table_functions, session, parent=base)
    # скалярные функции
    sfunc_data_set = conn.execute(sys_queries.all_scalar_functions)
    sfunctions = to_dict(base.name, original_models.OriginalScalarFunction, sfunc_data_set)
    sync_subordinate_members(sfunctions, base.scalar_functions, session, parent=base)
    # таблицы
    tables_data_set = conn.execute(sys_queries.all_tables)
    tables = to_dict(base.name, original_models.OriginalTable, tables_data_set)
    sync_subordinate_members(tables, base.tables, session, parent=base)
    # сопоставляем триггеры для оставшихся таблиц
    for table_name in base.tables:
        table = base.tables[table_name]
        triggers_data_set = conn.execute(
            sys_queries.triggers_for_table, table_id=table.database_object_id)
        triggers = to_dict(base.name, original_models.OriginalTrigger, triggers_data_set)
        sync_subordinate_members(triggers, table.triggers, session, table=table, database=base)
    # обновляем данные самой базы
    base.update_from(original_db)

def sync_separate_executable(ex, session, conn):
    """
    Синхронизирует отдельный выполняемый объект боевой БД 
    (представление, функцию, процедуру или триггер)
    """
    # определяем класс оригинала и запрос, с помощью которого будем получать оригинал
    # из боевой БД
    choices = {
        DBScalarFunction: {
            "original_class": original_models.OriginalScalarFunction,
            "query": sys_queries.get_specific_scalar_function
        },
        DBTableFunction: {
            "original_class": original_models.OriginalTableFunction,
            "query": sys_queries.get_specific_table_function
        },
        DBView: {
            "original_class": original_models.OriginalView,
            "query": sys_queries.get_specific_view
        },
        DBStoredProcedure: {
            "original_class": original_models.OriginalProcedure,
            "query": sys_queries.get_specific_procedure
        },
        DBTrigger: {
            "original_class": original_models.OriginalTrigger,
            "query": sys_queries.get_specific_trigger
        },
    }
    original_class = choices[ex.__class__]["original_class"]
    query = choices[ex.__class__]["query"]
    # достаём из базы оригинал
    record = conn.execute(query, id=ex.database_object_id)
    if record:
        original = original_class(**record)
        # сверяем даты обновления
        # если оригинал был изменён, синхронизируемся
        if original.last_update > ex.last_update:
            ex.update_from(original)
    else:
        # если оригинал не найден в боевой базе, то удаляем ноду
        session.delete(ex)

def sync_separate_table(table, session, conn):
    """
    Синхронизирует отдельную таблицу.
    """
    # достаём оригинал
    record = conn.execute(sys_queries.get_specific_table, id=table.database_object_id)
    if record:
        original_table = original_models.OriginalTable(**record)
        # сверяем даты обновления
        # если оригинал был изменён, синхронизируемся
        if original_table.last_update > table.last_update:
            table = session.query(DBTable).options(selectinload(DBTable.triggers))\
                .filter(DBTable.database_object_id == table.database_object_id).one()
            table.update_from(original_table)
            # тащим из базы все триггеры этой таблицы и сопоставляем их
            original_triggers = {}
            for row in conn.execute(sys_queries.triggers_for_table, table_id=table.id):
                trigger = original_models.OriginalTrigger(**row)
                original_triggers[trigger.name] = trigger
            sync_subordinate_members(original_triggers, table.triggers, session, parent=table)
    # если оригинал не найден в боевой базе, то удаляем таблицу
    else:
        session.delete(table)
