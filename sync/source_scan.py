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


def scan_separate_app(app, session):
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
    # ToDo
    # изменить запрос так, чтобы формы, коннекты и компоненты доставались через таблицу связей
    # должен получиться словарь {"forms": {}, "connections":{}}
    # "forms":{"path_to_form1":{"components":{}}, "path_to_form2":{"components"}}
    app = session.query(Application).\
        options(selectinload(Application.connections),\
        selectinload(Application.forms).\
        selectinload(Form.components)).filter(Application.id == app.id).one()
    scan_app(project, app, session)

def scan_app(original_project, project_pack, session):
    """
    Синхронизирует данные АРМа в базе с исходниками на диске.

    Метод парсит все формы, входящие в проект, чтобы собрать все соединения
    с базами, затем синхронизируются формы и их компоненты.
    """
    project_pack["node"].update_from(original_project)
    # разбираем оригиналы всех форм, входящих в проект, кладём в словарь, ключ - path
    parsed_forms = {path: DelphiForm(path) for path in original_project.forms}
    # формируем список соединений арма с базами и синхронизируем его
    original_connections = {}
    for form in parsed_forms:
        original_connections.update(parsed_forms[form].connections)
    link_to_app = []
    sync_subordinate_members(
        original_connections,
        project_pack["connections"],
        session,
        link_to_app)
    # сопоставляем списки форм, входящих в проект
    sync_subordinate_members(parsed_forms, project_pack["forms"], session, link_to_app)
    # list of actual connections
    # connection_pool = [conn for conn in session.dirty where isinstance(conn, ClientConnection)]
    # синхронизируем компонентых тех форм, которые остаются в базе
    for form in project_pack["forms"]:
        # выбираем из словаря оригинальных форм ту, которая соответствует обновляемой форме
        original = parsed_forms[form]
        sync_subordinate_members(
            original.queries,
            project_pack["forms"][form]["components"],
            session,
            link_to_app)
