import os
import datetime
from .delphi_classes import DelphiProject, DelphiForm
from sqlalchemy.orm import selectinload
from .common_functions import (
    sync_subordinate_members,
    get_remaining_objects)
from .common_classes import SyncException
from dpm.models import Application, Form
from typing import List, Dict


def sync_all_sources(delphi_dir_content: List, db_apps: Dict, session):
    """
    Синхронизирует всю кодовую базу.
    """
    projects = {path: DelphiProject(path) for path in delphi_dir_content}
    sync_subordinate_members(projects, db_apps, session)
    remaining_apps = get_remaining_objects(session, Application)
    ids = (item.id for item in remaining_apps)
    # запрашиваем данные по всем армам без ленивой загрузки,
    # то есть тащим из базы вообще всё: соединения, формы, компоненты
    apps_to_work = session.query(Application).options(\
        selectinload(Application.connections).selectinload(Application.forms).\
        selectinload(Form.components)).filter(Application.id.in_(ids)).all()
    for app in apps_to_work:
        original = projects[app.path]
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
    # обновляем саму форму
    form.update_from(parsed_form)
    refs = {"parent": form, "connections": form.application.connections}
    # синхронизируем компоненты
    sync_subordinate_members(
        parsed_form.queries,
        form.components,
        session,
        **refs)


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
    # разбираем оригиналы всех форм, входящих в проект, кладём в словарь, ключ - path
    parsed_forms = {path: DelphiForm(path) for path in project.forms}
    # формируем список соединений арма с базами и синхронизируем его
    original_connections = {}
    for form in parsed_forms:
        original_connections.update(parsed_forms[form].connections)
    sync_subordinate_members(
        original_connections,
        app.connections,
        session,
        parent=app)
    # сопоставляем списки форм, входящих в проект
    sync_subordinate_members(parsed_forms, app.forms, session, parent=app)
    # синхронизируем компонентых тех форм, которые остаются в базе
    for form in app.forms:
        # выбираем из словаря оригинальных форм ту, которая соответствует обновляемой форме
        original = parsed_forms[form]
        refs = {"parent": app.forms[form], "connections": app.connections}
        sync_subordinate_members(
            original.queries,
            app.forms[form].components,
            session,
            **refs)
