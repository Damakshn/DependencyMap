from dpm.models import (
    Database, 
    DBTable,
    DBScalarFunction,
    DBTableFunction,
    DBView,
    DBStoredProcedure,
    DBTrigger)
from sqlalchemy.orm import selectinload, joinedload
import sync.sys_queries as sys_queries
import sync.original_models as original_models
from .common_functions import (
    sync_subordinate_members,
    get_remaining_objects,
    make_named_dict,
    make_node_from)
from .common_classes import SyncException

def sync_database(base, session, conn):
    """
    Синхронизирует одну базу данных целиком.
    """
    # проверить дату последнего изменения метаданных базы
    meta = conn.execute(sys_queries.database_metadata).first()
    original_db = original_models.OriginalDatabase(**meta)
    # если определения объектов БД были изменены, синхронизируемся
    if original_db.last_update > base.last_update:
        # вытаскиваем всю хранимую информацию по базе без ленивой загрузки
        # todo add to database model fields for views, functions and so on
        # todo write query for database
        base = session.query(Database).options(
            selectinload(Database.views),
            selectinload(Database.procedures),
            selectinload(Database.table_functions),
            selectinload(Database.scalar_functions),
            selectinload(Database.tables),
            selectinload(Database.triggers)).filter(Database.id == base.id).one()
        base.update_from(original_db)
        # синхронизируем по очереди все типы объектов
        # процедуры
        proc_data_set = conn.execute(sys_queries.all_procedures)
        procedures = [original_models.OriginalProcedure(**row) for row in proc_data_set]
        sync_subordinate_members(procedures, base.procedures, session, parent=base)
        # представления
        views_data_set = conn.execute(sys_queries.all_views)
        views = [original_models.OriginalView(**row) for row in views_data_set]
        sync_subordinate_members(views, base.views, session, parent=base)
        # табличные функции
        tabfunc_data_set = conn.execute(sys_queries.all_table_functions)
        tfunctions = [original_models.OriginalTableFunction(**row) for row in tabfunc_data_set]
        sync_subordinate_members(tfunctions, base.table_functions, session, parent=base)
        # скалярные функции
        sfunc_data_set = conn.execute(sys_queries.all_scalar_functions)
        sfunctions = [original_models.OriginalScalarFunction(**row) for row in sfunc_data_set]
        sync_subordinate_members(sfunctions, base.scalar_functions, session, parent=base)
        # таблицы
        tables_data_set = conn.execute(sys_queries.all_tables)
        tables = [original_models.OriginalTable(**row) for row in tables_data_set]
        sync_subordinate_members(tables, base.tables, session, parent=base)
        # триггеры для оставшихся таблиц
        remaining_tables = get_remaining_objects(session, DBTable)
        for table in remaining_tables:
            triggers_data_set = conn.execute(
                sys_queries.triggers_for_table, table_id=table.database_object_id)
            triggers = [original_models.OriginalTrigger(**row) for row in triggers_data_set]
            sync_subordinate_members(triggers, table.triggers, session, table=table, database=base)

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
                .filter(DBTable.database_object_id == table.id).one()
            table.update_from(original_table)
            # тащим из базы все триггеры этой таблицы и сопоставляем их
            original_triggers = []
            for row in conn.execute(sys_queries.triggers_for_table, table_id=table.id):
                original_triggers.append(original_models.OriginalTrigger(**row))
            sync_subordinate_members(original_triggers, table.triggers, session, parent=table)
    # если оригинал не найден в боевой базе, то удаляем таблицу
    else:
        session.delete(table)
