import datetime
import json
from models import Application, Form, ClientConnection, ClientQuery, Link, Node
from delphitools import DelphiProject, DelphiForm, DelphiQuery, DelphiConnection
from sqlalchemy.orm import selectinload, joinedload
import os

class SyncException(Exception):
    pass

"""
Здесь содержится набор функций для синхронизации кодовой базы клиентских АРМов
с базой данных DPM.

Доступны следующие опции:
    * обновить всё - sync_all
    * обновить отдельный АРМ - sync_separate_app
    * обновить отдельную форму - sync_separate_form
    * обновить отдельный компонент - sync_separate_component

см. __all__ в конце.

Эти методы работают по следующей логике:
    На вход подаётся ORM-реализация обновляемого объекта, проверяется
    необходимость обновления, доступен ли объект в исходниках на диске,
    затем выполняется синхронизация.
"""

def sync_all(delphi_dir_content, db_apps, session):
    """
    Синхронизирует всю кодовую базу.
    """
    projects = [DelphiProject(path) for path in delphi_dir_content]
    sync_subordinate_members(projects, db_apps, session)
    apps_to_work = get_objects_to_sync(session, Application)
    ids = (item.id for item in apps_to_work)
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
    if not os.path.exists(app.path):
        session.delete(app)
        return
    project = DelphiProject(app.path)
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
    app.last_update = project.last_update
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
    forms_for_sync = get_objects_to_sync(session, Form)
    # получаем перечень актуальных соединений арма
    connections_dict = make_named_dict(get_objects_to_sync(session, ClientConnection))
    # составляем словарь оригинальных форм из исходников
    parsed_forms_dict = make_named_dict(parsed_forms)
    # синхронизируем компонентых тех форм, которые остаются в базе
    for f in forms_for_sync:
        # выбираем из словаря оригинальных форм ту, которая соответствует обновляемой форме
        original = parsed_forms_dict[f.path]
        refs = {"parent": f, "connections": connections_dict}
        sync_subordinate_members(original.queries, f.components, session, **refs)

def get_objects_to_sync(session, cls):
    """
    Возвращает список новых и изменённых объектов указанного класса в сессии.
    """
    # itertools.chain(l1, l2)
    # [*l1, *l2]
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
            # если новый объект участвует в построении графа зависимостей, то
            # нужно создать связь от родительского объекта к нему
            if isinstance(new_orm_object, Node) and not new_orm_object.is_root:
                parent = refs["parent"]
                session.add(Link(from_node=parent, to_node=new_orm_object))
        # объект есть и там, и там - сравнить и обновить, затем исключить объект из словаря
        elif item in replicas and needs_update(originals[item], replicas[item]):
            replicas[item].update_from(originals[item], **refs)
            del replicas[item]
    # в перечне объектов, сохранённых в базе остались только те, которые
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
        key = component_list[0].__class__.get_sync_key_field()
        for component in component_list:
            result[getattr(component, key)] = component
    return result

def make_orm_object_from(original, **refs):
    if isinstance(original, DelphiForm):
        return Form.create_from(original, **refs)
    if isinstance(original, DelphiQuery):
        return ClientQuery.create_from(original, **refs)
    if isinstance(original, DelphiProject):
        return Application.create_from(original, **refs)
    if isinstance(original, DelphiConnection):
        return ClientConnection.create_from(original, **refs)

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

__all__ = ["sync_all", "sync_separate_app", "sync_separate_form", "sync_separate_component"]
