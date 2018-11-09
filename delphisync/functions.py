import datetime
import json
from models import Application, Form, ClientConnection, ClientQuery, Link, Node
from delphitools import DelphiProject, DelphiForm, DelphiQuery, DelphiConnection
from sync_summary import SyncSummary
import os

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

Изменения выполняются не сразу, сначала они накапливаются в объекте SyncSummary.
Это нужно для более гибкого управления процессом синхронизации и вывода сообщений в процессе
обновления, чтобы пользователь понимал, что происходит в данный момент.
"""

def sync_all(delphi_dir_content, db_apps, session):
    """
    Синхронизирует всю кодовую базу.
    """
    projects = [DelphiProject(path) for path in delphi_dir_content]
    summary = sync_subordinate_members(projects, db_apps)
    apps_to_work = summary.get_persistent_objects(Application)
    # ToDo reload all persistent apps no lazy load
    projects_dict = make_named_dict(projects)
    for app in apps_to_work:
        original = projects_dict[app.path]
        summary.merge_with(sync_app(original, app))
    return summary

def sync_separate_app(app, session):
    """
    Синхронизирует отдельно взятый АРМ.
    """
    # ToDo expunge object from session if needed
    summary = SyncSummary()
    if not os.path.exists(app.path):
        summary.send_to_delete(app)
        return summary
    project = DelphiProject(app.path)
    if app.last_update == project.last_update:
        return summary
    # ToDo reload app with all dependencies, no lazy load
    summary.merge_with(sync_app(project, app))
    return summary

def sync_separate_form(form, session):
    """
    Синхронизирует отдельно взятую форму.
    """
    # ToDo expunge object from session if needed
    summary = SyncSummary()
   # отправляем форму на удаление, если она отсутствует на диске
    if not os.path.exists(form.path):
        summary.send_to_delete(form)
        return summary
    # если форма не изменилась со времени последнего обновления, то дальше не идём
    form_last_update = datetime.datetime.fromtimestamp(os.path.getmtime(form.path))
    if form_last_update == form.last_update:
        return summary
    # достаём оригинал из исходников
    parsed_form = DelphiForm(form.path)
    # reload form with no lazy load
    # get connection pool from form.application
    connections = {}
    # обновляем саму форму
    form.update_from(parsed_form)
    summary.send_to_update(form)
    refs = {"parent": form, "connections": connections}
    form_summary = sync_subordinate_members(parsed_form.queries, form.components, **refs)
    # синхронизируем компоненты
    summary.merge_with(form_summary)
    return summary

def sync_separate_component(component, session):
    """
    Синхронизирует отдельно взятый компонент
    """
    # ToDo expunge object from session if needed
    pass

def sync_app(project, app):
    """
    Синхронизирует данные АРМа в базе с исходниками на диске.

    Метод парсит все формы, входящие в проект, чтобы собрать все соединения
    с базами, затем синхронизируются формы и их компоненты.
    """
    summary = SyncSummary()
    app.last_update = project.last_update
    summary.send_to_update(app)
    # разбираем оригиналы всех форм, входящих в проект
    parsed_forms = [DelphiForm(form["path"]) for form in project.forms]
    # формируем список соединений арма с базами и синхронизируем его
    connection_pool = []
    for form in parsed_forms:
        connection_pool.extend(form.connections)
    connections_to_sync = sync_subordinate_members(connection_pool, app.connections, parent=app)
    summary.merge_with(connections_to_sync)
    # сопоставляем списки форм, входящих в проект
    forms_to_sync = sync_subordinate_members(parsed_forms, app.forms, parent=app)
    summary.merge_with(forms_to_sync)
    # готовим синхронизацию компонентов форм
    # получаем список форм, которые остаются в базе
    forms_for_sync = summary.get_persistent_objects(Form)
    # получаем перечень актуальных соединений арма, теперь connection_pool - это словарь
    connection_pool = make_named_dict(summary.get_persistent_objects(ClientConnection))
    # составляем словарь оригинальных форм из исходников
    parsed_forms_dict = make_named_dict(parsed_forms)
    # синхронизируем компонентых тех форм, которые остаются в базе
    for f in forms_for_sync:
        # выбираем из словаря оригинальных форм ту, которая соответствует обновляемой форме
        original = parsed_forms_dict[f.path]
        refs = {"parent": f, "connections": connection_pool}
        form_summary = sync_subordinate_members(original.queries, f.components, **refs)
        summary.merge_with(form_summary)
    return summary

def sync_form_components(parsed_form, form, connections):
    """
    Синхронизирует компоненты на форме.
    """
    # синхронизируем компоненты на форме
    refs = {"parent": form, "connections": connections}
    components_to_sync = sync_subordinate_members(parsed_form.queries, form.components, **refs)
    return components_to_sync

def sync_subordinate_members(original_items, db_items, **refs) -> SyncSummary:
    """
    Сопоставляет 2 списка объектов: актуальные объекты в исходниках на диске
    и их реплики в виде объектов ORM, взятых из БД.

    Метод определяет, какие объекты должны быть созданы, изменены или удалены.
    Возвращает объект SyncSummary, содержащий объекты ORM, поделённые на 3 соответствующие категории.

    Третий параметр - ссылки на другие ORM-модели, которые нужно прикрепить при создании/обновлении.
    """
    summary = SyncSummary()
    # превращаем поданные на вход списки в словари, чтобы их было проще сравнивать поэлементно
    originals = make_named_dict(original_items)
    replicas = make_named_dict(db_items)
    for item in originals:
        # объект есть на диске, но отсутствует в БД - создать
        if item not in replicas:
            new_orm_object = make_orm_object_from(originals[item], **refs)
            summary.send_to_create(new_orm_object)
            # если новый объект участвует в построении графа зависимостей, то
            # нужно создать связь от родительского объекта к нему
            if isinstance(new_orm_object, Node) and not new_orm_object.is_root:
                parent = refs["parent"]
                summary.send_to_create(
                    Link(from_node=parent, to_node=new_orm_object)
                )
        # объект есть и там, и там - сравнить и обновить, затем исключить объект из словаря
        elif item in replicas and needs_update(originals[item], replicas[item]):
            replicas[item].update_from(originals[item], **refs)
            summary.send_to_update(replicas[item])
            del replicas[item]
    # в перечне объектов, сохранённых в базе остались только те, которые
    # не имеют оригинала в исходниках, их надо удалить
    for item in replicas:
        summary.send_to_delete(replicas[item])
    return summary

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
            result[component[key]] = component
    return result

def make_orm_object_from(original, **refs):
    if isinstance(original, DelphiForm):
        return Form.create_from(original, **refs)
    if isinstance(original, DelphiQuery):
        return ClientQuery.create_from(original, **refs)
    if isinstance(original, DelphiProject):
        return Application.create_from(original, **refs)

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

__all__ = [sync_all, sync_separate_app,.sync_separate_form, sync_separate_component]
