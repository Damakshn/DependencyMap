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
    DBScript)
import sync.original_models as original_models
from .common_functions import (
    sync_subordinate_members,
    get_remaining_objects)
from typing import List, Dict
import itertools
import logging


def sync_database(base, session, conn):
    """
    Синхронизирует одну базу данных целиком.
    """
    logging.debug(f"Достаём оригинал базы данных {base.name}")
    original_db = original_models.OriginalDatabase.fetch_from_metadata(conn)
    if original_db.last_update == base.last_update:
        logging.info(f"В оригинальной БД не было изменений, выходим")
        return
    logging.debug(f"Вытаскиваем всю хранимую информацию по БД {base.name} без ленивой загрузки")
    base = session.query(Database).options(
        selectinload(Database.scripts).selectinload(DBScript.references),
        selectinload(Database.tables)
    ).filter(Database.id == base.id).one()
    logging.debug(f"Синхронизируем по очереди все типы объектов БД {base.name}")
    logging.debug(f"Синхронизируем процедуры БД {base.name}")
    proc_data_set = original_models.OriginalProcedure.get_all(conn)
    sync_subordinate_members(proc_data_set, base.procedures, session, parent=base)
    logging.debug(f"Синхронизируем представления БД {base.name}")
    views_data_set = original_models.OriginalView.get_all(conn)
    sync_subordinate_members(views_data_set, base.views, session, parent=base)
    logging.debug(f"Синхронизируем табличные функции БД {base.name}")
    tabfunc_data_set = original_models.OriginalTableFunction.get_all(conn)
    sync_subordinate_members(tabfunc_data_set, base.table_functions, session, parent=base)
    logging.debug(f"Синхронизируем скалярные функции БД {base.name}")
    sfunc_data_set = original_models.OriginalScalarFunction.get_all(conn)
    sync_subordinate_members(sfunc_data_set, base.scalar_functions, session, parent=base)
    logging.debug(f"Синхронизируем таблицы БД {base.name}")
    tables_data_set = original_models.OriginalTable.get_all(conn)
    sync_subordinate_members(tables_data_set, base.tables, session, parent=base)
    logging.debug(f"Сопоставляем триггеры для оставшихся таблиц БД {base.name}")
    for table_name in base.tables:
        logging.debug(f"Собираем триггеры для таблицы {table_name} в БД {base.name}")
        table = base.tables[table_name]
        triggers_data_set = original_models.OriginalTrigger.get_triggers_for_table(
            conn, table.database_object_id)
        sync_subordinate_members(triggers_data_set, table.triggers, session, table=table, database=base)
    logging.debug(f"Синхронизируем системные зависимости скриптов в БД {base.name}")
    for script_name in base.scripts:
        logging.debug(f"Обрабатываем зависимости скрипта {script_name}")
        script = base.scripts[script_name]
        try:
            ref_data_set = original_models.\
                OriginalSystemReferense.get_references_for_object(conn, script.long_name)
            sync_subordinate_members(ref_data_set, script.references, session, parent=script)
        except Exception as e:
            logging.error(f"Не удалось запросить у SQL Server зависимости {script_name}, ошибка - \n{e}")
            script.is_broken = True
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
