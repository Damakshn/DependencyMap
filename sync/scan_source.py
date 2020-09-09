import itertools
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from dpm.models import Form, ClientQuery, Database
from .common_functions import sync_subordinate_members
from .delphi_classes import DelphiProject


def scan_application(app, session):
    original_project = DelphiProject(app.path)
    # продолжать только если требуется обновление
    if (original_project.last_update is None) or (original_project.last_update <= app.last_update):
        return
    # достаём из системы список доступных баз, чтобы прицепить к ним компоненты
    available_databases = {db.name: db for db in session.query(Database).all()}
    default_database = app.default_database
    # достаём из базы формы, либо имеющие такой же путь, как в конфиге проекта
    # либо прикреплённые к проекту ранее
    # это позволяет обойти проблемы, возникающие от того, существуют формы, общие для нескольких проектов
    condition = or_(Form.applications.any(id=app.id), Form.path.in_(original_project.forms.keys()))
    form_nodes = {
        form.path: form
        for form in session.query(Form).options(selectinload(Form.applications), selectinload(Form.components)).filter(condition)
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
            new_form = Form.create_from(original_form, app)
            new_form.applications.append(app)
            dirty_forms[form_path] = new_form

    # выявляем формы, выбывшие из проекта
    for form_path in form_nodes:
        form_node = form_nodes[form_path]
        if not (form_path in original_project.forms):
            if form_node.is_shared:
                app.forms.remove(form_node)
            else:
                session.delete(form_node)

    # парсим все формы, обновляем компоненты только на новых/изменившихся
    connection_pool = {}
    for form_path in original_project.forms:
        # собираем коннекты со всех распарсенных форм
        connection_pool.update(original_project.forms[form_path].connections)
        if form_path in dirty_forms:
            sync_subordinate_members(
                original_project.forms[form_path].queries,
                ClientQuery,
                dirty_forms[form_path].components,
                session,
                dirty_forms[form_path]
            )
    persistent_components = [component for component in session if isinstance(component, ClientQuery)]

    original_components = {component[0]: component[1] for component in itertools.chain.from_iterable([form.queries.items() for form in original_project.forms.values()])}

    for component in persistent_components:
        original_component = original_components[component.name]
        conn = connection_pool.get(original_component.connection)
        if conn is not None:
            component.database = available_databases.get(conn.database)
        else:
            component.database = default_database
