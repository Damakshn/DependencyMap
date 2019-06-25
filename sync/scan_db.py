from sqlalchemy.orm import selectinload, joinedload
from .common_classes import SyncException
from dpm.models import (
    Database,
    DBTable,
    DBScalarFunction,
    DBTableFunction,
    DBView,
    DBStoredProcedure,
    DBTrigger,
    DBScript,
    Edge)
import sync.original_models as original_models
from .common_functions import (
    sync_subordinate_members,
    get_remaining_objects)
from typing import List, Dict
import itertools
import logging


def scan_database(base, session, conn):
    """
    Синхронизирует одну базу данных целиком.
    """
    original_db = original_models.OriginalDatabase.fetch_from_metadata(conn)
    if original_db.last_update == base.last_update:
        logging.info(f"В оригинальной БД не было изменений, выходим")
        return
    base = session.query(Database).options(
        selectinload(Database.scripts),
        selectinload(Database.tables)
    ).filter(Database.id == base.id).one()
    
    logging.debug(f"Достаём оригиналы объектов БД {base.name}")
    original_proc_data_set = original_models.OriginalProcedure.get_all(conn)
    original_views_data_set = original_models.OriginalView.get_all(conn)
    original_tabfunc_data_set = original_models.OriginalTableFunction.get_all(conn)
    original_sfunc_data_set = original_models.OriginalScalarFunction.get_all(conn)
    original_tables_data_set = original_models.OriginalTable.get_all(conn)
    
    logging.debug(f"Синхронизируем хранимые процедуры БД {base.name}")
    sync_subordinate_members(original_proc_data_set, DBStoredProcedure, base.procedures, session, base)
    
    logging.debug(f"Синхронизируем представления БД {base.name}")
    sync_subordinate_members(original_views_data_set, DBView, base.views, session, base)

    logging.debug(f"Синхронизируем табличные функции БД {base.name}")
    sync_subordinate_members(original_tabfunc_data_set, DBTableFunction, base.table_functions, session, base)

    logging.debug(f"Синхронизируем скалярные функции БД {base.name}")
    sync_subordinate_members(original_sfunc_data_set, DBScalarFunction, base.scalar_functions, session, base)

    logging.debug(f"Синхронизируем таблицы БД {base.name}")
    sync_subordinate_members(original_tables_data_set, DBTable, base.tables, session, base)
    persistent_tables = {table.name: table for table in session if isinstance(table, DBTable)}
    
    logging.debug(f"Сопоставляем триггеры для оставшихся таблиц БД {base.name}")
    for table_name in persistent_tables:
        table = persistent_tables[table_name]
        logging.debug(f"Собираем триггеры для таблицы {table_name} в БД {base.name}")
        original_triggers_data_set = original_models.OriginalTrigger.get_triggers_for_table(conn, table.database_object_id)
        sync_subordinate_members(
            original_triggers_data_set,
            DBTrigger, 
            table.triggers, 
            session,
            table
        )
    
    # обновляем метаданные самой базы
    base.update_from(original_db)
    logging.info(f"Обработка базы {base.name} завершена")


def sync_separate_script(script, session, conn):
    """
    Синхронизирует отдельный выполняемый объект боевой БД
    (представление, функцию, процедуру или триггер)
    """
    # определяем класс оригинала и запрос, с помощью которого
    # будем получать оригинализ боевой БД
    choices = {
        DBScalarFunction: original_models.OriginalScalarFunction,
        DBTableFunction: original_models.OriginalTableFunction,
        DBView: original_models.OriginalView,
        DBStoredProcedure: original_models.OriginalProcedure,
        DBTrigger: original_models.OriginalTrigger,
    }
    original_class = choices[script.__class__]
    # достаём из базы оригинал
    original = original_class.get_by_id(conn, script.database_object_id)
    if original:
        # сверяем даты обновления
        # если оригинал был изменён, синхронизируемся
        if original.last_update > script.last_update:
            script.update_from(original)
    else:
        # если оригинал не найден в боевой базе, то удаляем ноду
        session.delete(script)


def sync_separate_table(table, session, conn):
    """
    Синхронизирует отдельную таблицу.
    """
    # достаём оригинал
    original = original_models.OriginalTable.get_by_id(conn, table.database_object_id)
    if original:
        # сверяем даты обновления
        # если оригинал был изменён, синхронизируемся
        if original.last_update > table.last_update:
            table = session.query(DBTable).options(selectinload(DBTable.triggers))\
                .filter(DBTable.database_object_id == table.database_object_id).one()
            table.update_from(original)
            # тащим из базы все триггеры этой таблицы и сопоставляем их
            original_triggers = original_models.OriginalTrigger.get_triggers_for_table(conn, table.id)
            sync_subordinate_members(original_triggers, table.triggers, session, parent=table)
    # если оригинал не найден в боевой базе, то удаляем таблицу
    else:
        session.delete(table)
