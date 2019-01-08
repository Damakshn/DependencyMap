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
import sync.original_models as original_models
from .common_functions import (
    sync_subordinate_members,
    get_remaining_objects,
    make_node_from)
from typing import List, Dict
import itertools


def sync_database(base, session, conn):
    """
    Синхронизирует одну базу данных целиком.
    """
    # достаём оригинал базы данных
    original_db = original_models.OriginalDatabase.fetch_from_metadata(conn)
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
    proc_data_set = original_models.OriginalProcedure.get_all(conn)
    sync_subordinate_members(proc_data_set, base.procedures, session, parent=base)
    # представления
    views_data_set = original_models.OriginalView.get_all(conn)
    sync_subordinate_members(views_data_set, base.views, session, parent=base)
    # табличные функции
    tabfunc_data_set = original_models.OriginalTableFunction.get_all(conn)
    sync_subordinate_members(tabfunc_data_set, base.table_functions, session, parent=base)
    # скалярные функции
    sfunc_data_set = original_models.OriginalScalarFunction.get_all(conn)
    sync_subordinate_members(sfunc_data_set, base.scalar_functions, session, parent=base)
    # таблицы
    tables_data_set = original_models.OriginalTable.get_all(conn)
    sync_subordinate_members(tables_data_set, base.tables, session, parent=base)
    # сопоставляем триггеры для оставшихся таблиц
    for table_name in base.tables:
        table = base.tables[table_name]
        triggers_data_set = original_models.OriginalTrigger.get_triggers_for_table(
            conn, table.database_object_id)
        sync_subordinate_members(triggers_data_set, table.triggers, session, table=table, database=base)
    # обновляем данные самой базы
    base.update_from(original_db)

def sync_separate_script(script, session, conn):
    """
    Синхронизирует отдельный выполняемый объект боевой БД 
    (представление, функцию, процедуру или триггер)
    """
    # определяем класс оригинала и запрос, с помощью которого будем получать оригинал
    # из боевой БД
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
            # ToDo должен быть словарь
            original_triggers = original_models.OriginalTrigger.get_triggers_for_table(conn, table.id)
            sync_subordinate_members(original_triggers, table.triggers, session, parent=table)
    # если оригинал не найден в боевой базе, то удаляем таблицу
    else:
        session.delete(table)
