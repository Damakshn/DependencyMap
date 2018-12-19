import os
import datetime
from models import (
    Application,
    Form, 
    ClientConnection, 
    ClientQuery, 
    Link, 
    Node, 
    Database, 
    DBTable,
    DBScalarFunction,
    DBTableFunction,
    DBView,
    DBStoredProcedure,
    DBTrigger)
from delphi_classes import DelphiProject, DelphiForm, DelphiQuery, DelphiConnection
from sqlalchemy.orm import selectinload, joinedload
import sync.sys_queries as sys_queries
import sync.original_models as original_models


class SyncException(Exception):
    pass

"""
Здесь содержится набор функций для синхронизации кодовой базы клиентских АРМов
с базой данных DPM.

Доступны следующие опции:
    * обновить всё - sync_all_sources
    * обновить отдельный АРМ - sync_separate_app
    * обновить отдельную форму - sync_separate_form
    * обновить отдельный компонент - sync_separate_component

см. __all__ в конце.

Эти методы работают по следующей логике:
    На вход подаётся ORM-реализация обновляемого объекта, проверяется
    необходимость обновления, доступен ли объект в исходниках на диске,
    затем выполняется синхронизация.
"""

def sync_all_sources(delphi_dir_content, db_apps, session):
    """
    Синхронизирует всю кодовую базу.
    """
    projects = [DelphiProject(path) for path in delphi_dir_content]
    sync_subordinate_members(projects, db_apps, session)
    remaining_apps = get_remaining_objects(session, Application)
    ids = (item.id for item in remaining_apps)
    # запрашиваем данные по всем армам без ленивой загрузки,
    # то есть тащим из базы вообще всё: соединения, формы, компоненты
    apps_to_work = session.query(Application).options(\
        selectinload(Application.connections).selectinload(Application.forms).\
        selectinload(Form.components)).filter(Application.id.in_(ids)).all()
    projects_dict = make_named_dict(projects)
    for app in apps_to_work:
        original = projects_dict[app.path]
        sync_app(original, app, session)

def sync_separate_app(app, session):
    """
    Синхронизирует отдельно взятый АРМ.
    """
    # если оригинал проекта не найден, удаляем ноду из базы
    if not os.path.exists(app.path):
        session.delete(app)
        return
    # парсим файл проекта
    project = DelphiProject(app.path)
    # если оригинал изменился, то загружаем из базы все данные по АРМу
    # и синхронизируемся
    if project.last_update <= app.last_update:
        return
    app = session.query(Application).\
        options(selectinload(Application.connections),\
        selectinload(Application.forms).\
        selectinload(Form.components)).filter(Application.id == app.id).one()
    sync_app(project, app, session)

def sync_separate_form(form, session):
    """
    Синхронизирует отдельно взятую форму.
    """
   # отправляем форму на удаление, если она отсутствует на диске
    if not os.path.exists(form.path):
        session.delete(form)
        return
    # если форма не изменилась со времени последнего обновления, то дальше не идём
    form_last_update = datetime.datetime.fromtimestamp(os.path.getmtime(form.path))
    if form_last_update <= form.last_update:
        return
    # достаём оригинал из исходников
    parsed_form = DelphiForm(form.path)
    """
    Повторно запрашиваем форму из базы, достаём сразу
    информацию об АРМе, его соединениях и о компонентах формы.
    """    
    form = session.query(Form).options(selectinload(Form.components).\
        joinedload(Form.application).\
        selectinload(Application.connections)).\
        filter(Form.id == form.id).one()
    connections = make_named_dict(form.application.connections)
    # обновляем саму форму
    form.update_from(parsed_form)
    refs = {"parent": form, "connections": connections}
    # синхронизируем компоненты
    sync_subordinate_members(parsed_form.queries, form.components, session, **refs)

def sync_separate_component(component, session):
    """
    Синхронизирует отдельно взятый компонент
    """
    form_path = component.form.path
    """
    если файл отсутствует на диске, то не предпринимаем никаких
    действий, форму из базы не удаляем, для этого есть другой метод
    просто кидаем исключение
    """
    if not os.path.exists(form_path):
        raise SyncException(f"Файл формы {form_path} не найден.")
    # парсим форму, достаём оригинал компонента
    parsed_form = DelphiForm(form_path)
    found = False
    i = 0
    while not found or i < len(parsed_form.queries):
        if parsed_form.queries[i].name == component.name:
            found = True
    # в зависимости от того, нашли мы оригинал или нет, удаляем или обновляем компонент
    if not found:
        session.delete(component)
    else:
        if parsed_form.queries[i].crc32 != component.crc32:
            component.update_from(parsed_form.queries[i])

def sync_app(project, app, session):
    """
    Синхронизирует данные АРМа в базе с исходниками на диске.

    Метод парсит все формы, входящие в проект, чтобы собрать все соединения
    с базами, затем синхронизируются формы и их компоненты.
    """
    app.update_from(project)
    # разбираем оригиналы всех форм, входящих в проект
    parsed_forms = [DelphiForm(form["path"]) for form in project.forms]
    # формируем список соединений арма с базами и синхронизируем его
    connection_list = []
    for form in parsed_forms:
        connection_list.extend(form.connections)
    sync_subordinate_members(connection_list, app.connections, session, parent=app)
    # сопоставляем списки форм, входящих в проект
    sync_subordinate_members(parsed_forms, app.forms, session, parent=app)
    # готовим синхронизацию компонентов форм
    # получаем список форм, которые остаются в базе
    remaining_forms = get_remaining_objects(session, Form)
    # получаем перечень актуальных соединений арма
    connections_dict = make_named_dict(get_remaining_objects(session, ClientConnection))
    # составляем словарь оригинальных форм из исходников
    parsed_forms_dict = make_named_dict(parsed_forms)
    # синхронизируем компонентых тех форм, которые остаются в базе
    for f in remaining_forms:
        # выбираем из словаря оригинальных форм ту, которая соответствует обновляемой форме
        original = parsed_forms_dict[f.path]
        refs = {"parent": f, "connections": connections_dict}
        sync_subordinate_members(original.queries, f.components, session, **refs)

def get_remaining_objects(session, cls):
    """
    Возвращает список объектов в сессии, оставшихся после удаления.
    """
    result = [item for item in session.dirty if isinstance(item, cls)]
    result.extend([item for item in session.new if isinstance(item, cls)])
    return result

def sync_subordinate_members(original_items, db_items, session, **refs):
    """
    Сопоставляет 2 списка объектов: актуальные объекты в исходниках на диске
    и их реплики в виде объектов ORM, взятых из БД.

    Метод определяет, какие объекты должны быть созданы, изменены или удалены.

    Четвёртый параметр - ссылки на другие ORM-модели, которые нужно прикрепить при создании/обновлении.
    """
    # превращаем поданные на вход списки в словари, чтобы их было проще сравнивать поэлементно
    originals = make_named_dict(original_items)
    replicas = make_named_dict(db_items)
    for item in originals:
        # объект есть на диске, но отсутствует в БД - создать
        if item not in replicas:
            new_orm_object = make_orm_object_from(originals[item], **refs)
            session.add(new_orm_object)
            # если новый объект не является корневым узлом, то
            # нужно создать связь от родительского объекта к нему
            if not new_orm_object.is_root:
                if not isinstance(new_orm_object, DBTrigger):
                    parent = refs["parent"]
                    session.add(Link(from_node=parent, to_node=new_orm_object))
                else:
                    parent_table = refs["table"]
                    parent_db = refs["database"]
                    session.add(Link(from_node=parent_table, to_node=new_orm_object))
                    session.add(Link(from_node=parent_db, to_node=new_orm_object))
        # объект есть и там, и там - сравнить и обновить, затем исключить объект из словаря
        elif item in replicas and needs_update(originals[item], replicas[item]):
            replicas[item].update_from(originals[item], **refs)
            del replicas[item]
    # в перечне объектов, лежащих сейчас в базе, остались только те, которые
    # не имеют оригинала в исходниках, их надо удалить
    for item in replicas:
        session.delete(replicas[item])

def make_named_dict(component_list):
    """
    Вспомогательный метод, упрощающий отсев объектов синхронизации.

    Преобразует список объектов (выбранных из базы или полученных
    из исходников) в словарь вида "идентификатор_компонента": компонент.

    Имя поля-идентификатора зависит от класса упаковываемых объектов.
    Если на входе будет пустой список, на выходе будет пустой словарь.
    """
    result = {}
    if component_list:
        key = component_list[0].__class__.key_field()
        for component in component_list:
            result[getattr(component, key)] = component
    return result

def make_orm_object_from(original, **refs):
    """
    Создаёт новую ноду, класс которой соответствует классу оригинала.

    По-моему, этот метод ужасен.
    """
    # ноды клиента - АРМы, формы, компоненты, соединения
    if isinstance(original, DelphiForm):
        return Form.create_from(original, **refs)
    if isinstance(original, DelphiQuery):
        return ClientQuery.create_from(original, **refs)
    if isinstance(original, DelphiProject):
        return Application.create_from(original, **refs)
    if isinstance(original, DelphiConnection):
        return ClientConnection.create_from(original, **refs)
    # ноды баз данных - процедуры, вьюхи, функции, таблицы, триггеры
    if isinstance(original, original_models.OriginalProcedure):
        return DBStoredProcedure.create_from(original, **refs)
    if isinstance(original, original_models.OriginalTrigger):
        return DBTrigger.create_from(original, **refs)
    if isinstance(original, original_models.OriginalView):
        return DBView.create_from(original, **refs)
    if isinstance(original, original_models.OriginalTableFunction):
        return DBTableFunction.create_from(original, **refs)
    if isinstance(original, original_models.OriginalScalarFunction):
        return DBScalarFunction.create_from(original, **refs)
    if isinstance(original, original_models.OriginalTable):
        return DBTable.create_from(original, **refs)

def needs_update(obj_from_disk, obj_from_db):
    """
    Сравнивает реализацию объекта из исходников на диске с реализацией
    в виде ORM-объекта, взятой из БД.

    Критерий сравнения выбирается в зависимости от типа сравниваемых сущностей.
    Возвращает True, если объект из базы устарел и должен быть обновлён.
    """
    if isinstance(obj_from_db, Form):
        return obj_from_db.last_update < obj_from_disk.last_update
    if isinstance(obj_from_db, ClientQuery):
        return obj_from_db.crc32 != obj_from_disk.crc32
    if isinstance(obj_from_db, Application):
        return obj_from_db.last_update < obj_from_disk.last_update
    return True

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


__all__ = ["sync_all_sources", "sync_separate_app", "sync_separate_form", "sync_separate_component"]
