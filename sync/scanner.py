import logging
import itertools
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from dpm.connector import Connector
from dpm import models
from sync import original_models
from sync.common_functions import sync_subordinate_members
from sync.delphi_classes import DelphiProject

logger = logging.getLogger(__name__)


class DpmScanner:

    def __init__(self, connection_data):
        self._connector = Connector(**connection_data)
        self._session = self._connector.connect_to_dpm()
        self._applications = []
        self._databases = []

    def load_applications(self, data):
        for application_name in data:
            try:
                application = self._session.query(models.Application).filter_by(name=application_name).one()
            except NoResultFound:
                application = models.Application(
                    path=data[application_name]["path"],
                    name=application_name,
                    default_database=data[application_name]["default_database"],
                    cod_application=data[application_name].get("cod_application")
                )
            except MultipleResultsFound:
                logger.error(f"Найдены 2 или более приложения {application_name}, сканирование проводиться не будет")
            self._applications.append(application)

    def load_databases(self, data):
        for database_name in data:
            try:
                database = self._session.query(models.Database).filter_by(name=database_name).one()
            except NoResultFound:
                database = models.Database(
                    name=database_name
                )
            except MultipleResultsFound:
                logger.error(f"Найдены 2 или более БД {database_name}, сканирование проводиться не будет")
            self._databases.append(database)

    def _scan_application(self, app):
        original_project = DelphiProject(app.path)
        # продолжать только если требуется обновление
        if (app.last_update is not None) and (original_project.last_update <= app.last_update):
            return
        # достаём из системы список доступных баз, чтобы прицепить к ним компоненты
        available_databases = {db.name: db for db in self._session.query(models.Database).all()}
        default_database = app.default_database
        # достаём из базы формы, либо имеющие такой же путь, как в конфиге проекта
        # либо прикреплённые к проекту ранее
        # это позволяет обойти проблемы, возникающие от того, существуют формы, общие для нескольких проектов
        condition = or_(models.Form.applications.any(id=app.id), models.Form.path.in_(original_project.forms.keys()))
        form_nodes = {
            form.path: form
            for form in self._session.query(models.Form).options(
                selectinload(models.Form.applications), selectinload(models.Form.components)
            ).filter(condition)
        }
        # словарь форм, которые надо будет распарсить и залить/перезалить их компоненты в ДПМ
        dirty_forms = {}
        # сверяясь с конфигом проекта, ищем формы, которые надо обновить/добавить
        for form_path in original_project.forms:
            original_form = original_project.forms[form_path]
            original_form.parse()
            form_node = form_nodes.get(form_path)
            if form_node is not None:
                if not (app in form_node.applications):
                    form_node.applications.append(app)
                if (original_form.last_update > form_node.last_update):
                    form_node.update_from(original_form)
                    dirty_forms[form_path] = form_node
            else:
                new_form = models.Form.create_from(original_form, app)
                new_form.applications.append(app)
                dirty_forms[form_path] = new_form

        # выявляем формы, выбывшие из проекта
        for form_path in form_nodes:
            form_node = form_nodes[form_path]
            if not (form_path in original_project.forms):
                if form_node.is_shared:
                    app.forms.remove(form_node)
                else:
                    self._session.delete(form_node)

        # парсим все формы, обновляем компоненты только на новых/изменившихся
        connection_pool = {}
        for form_path in original_project.forms:
            # собираем коннекты со всех распарсенных форм
            connection_pool.update(original_project.forms[form_path].connections)
            if form_path in dirty_forms:
                sync_subordinate_members(
                    original_project.forms[form_path].queries,
                    models.ClientQuery,
                    dirty_forms[form_path].components,
                    self._session,
                    dirty_forms[form_path]
                )
        persistent_components = [component for component in self._session if isinstance(component, models.ClientQuery)]

        original_components = {
            component[0]: component[1]
            for component in itertools.chain.from_iterable(
                [form.queries.items() for form in original_project.forms.values()]
            )}

        for component in persistent_components:
            original_component = original_components[component.name]
            conn = connection_pool.get(original_component.connection)
            if conn is not None:
                component.database = available_databases.get(conn.database)
            else:
                component.database = default_database

    def _scan_database(self, database):
        conn = self._connector.connect_to(database)
        original_db = original_models.OriginalDatabase.fetch_from_metadata(conn)
        if original_db.last_update == database.last_update:
            logger.info("В оригинальной БД не было изменений, выходим")
            return
        database = self._session.query(models.Database).options(
            selectinload(models.Database.scripts),
            selectinload(models.Database.tables)
        ).filter(models.Database.id == database.id).one()

        logger.debug(f"Достаём оригиналы объектов БД {database.name}")
        original_proc_data_set = original_models.OriginalProcedure.get_all(conn)
        original_views_data_set = original_models.OriginalView.get_all(conn)
        original_tabfunc_data_set = original_models.OriginalTableFunction.get_all(conn)
        original_sfunc_data_set = original_models.OriginalScalarFunction.get_all(conn)
        original_tables_data_set = original_models.OriginalTable.get_all(conn)

        logger.debug(f"Синхронизируем хранимые процедуры БД {database.name}")
        sync_subordinate_members(
            original_proc_data_set,
            models.DBStoredProcedure,
            database.procedures,
            self._session, database
        )

        logger.debug(f"Синхронизируем представления БД {database.name}")
        sync_subordinate_members(
            original_views_data_set,
            models.DBView,
            database.views,
            self._session, database
        )

        logger.debug(f"Синхронизируем табличные функции БД {database.name}")
        sync_subordinate_members(
            original_tabfunc_data_set,
            models.DBTableFunction,
            database.table_functions,
            self._session, database
        )

        logger.debug(f"Синхронизируем скалярные функции БД {database.name}")
        sync_subordinate_members(
            original_sfunc_data_set,
            models.DBScalarFunction,
            database.scalar_functions,
            self._session, database
        )

        logger.debug(f"Синхронизируем таблицы БД {database.name}")
        sync_subordinate_members(
            original_tables_data_set,
            models.DBTable,
            database.tables,
            self._session, database
        )
        persistent_tables = {table.name: table for table in self._session if isinstance(table, models.DBTable)}

        logger.debug(f"Сопоставляем триггеры для оставшихся таблиц БД {database.name}")
        for table_name in persistent_tables:
            table = persistent_tables[table_name]
            logger.debug(f"Собираем триггеры для таблицы {table_name} в БД {database.name}")
            original_triggers_data_set = original_models.OriginalTrigger.get_triggers_for_table(
                conn,
                table.database_object_id
            )
            sync_subordinate_members(
                original_triggers_data_set,
                models.DBTrigger,
                table.triggers,
                self._session,
                table
            )

    def run_scanning(self):
        for application in self._applications:
            self._scan_application(application)
        for database in self._databases:
            self._scan_database(database)
