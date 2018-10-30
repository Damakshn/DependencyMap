import datetime
import json
from models import Application, Form, ClientConnection, ClientQuery, Link, SessionDPM
from delphitools import DelphiProject, DelphiForm, DelphiQuery, DelphiConnection
import os.path


class SyncSummary:
    
    def __init__(self):
        pass
    
    @property
    def empty(self):
        return True
    
    def to_create(self, data):
        pass
    
    def to_update(self, data):
        pass
    
    def to_delete(self, data):
        pass
    
    @property
    def description(self):
        return f""
    
    def apply_changes(self, session):
        pass

session = SessionDPM()
NOW = datetime.datetime.now()

def get_new_sync_summary():
    """
    Возвращает новый каталог объектов синхронизации,
    стандартный для всех синхронизирующих методов
    """
    return {
        "create": [],
        "update": [],
        "delete": []
    }

def merge_summaries(parent, child):
    """
    Сливает два каталога синхронизации - родительский и дочерний,
    который получился в результате обработки подчинённого объекта.
    В результате слияния данные из дочернего компонента сливаются в
    родительский.
    """
    for key in parent:
        parent[key].extend(child[key])
    
def make_component_dict(components_list):
    """
    Преобразует список компонентов (выбранных из базы или полученных
    после парсинга файла формы) в словарь вида "имя_компонента": компонент
    """
    result = {}
    for component in components_list:
        result[component["name"]] = component
    return result

# метод синхронизации должен возвращать каталог объектов
# добавить, обновить и удалить

def sync_node(node_id):
    pass
    # determine type of node
    # call the appropriate method

def sync_component(component):
    # ? connections
    # component.form.application.connections
    pass
    # get form
    # parse form
    # no form - throw error
    # find component in parsed form
    # no component on form - delete from db
    # compare crc32
    # if different - update
    # create new object for brand new component

def sync_form(form, connections):
    """
    Синхронизирует отдельно взятую форму.
    """
    summary = get_new_sync_summary()
    if not os.path.exists(form.path):
        # отправляем форму на удаление, если она отсутствует на диске
        return summary
    # парсим форму, списываем дату обновления
    parsed_form = DelphiForm(form.path)
    form.last_update = parsed_form.last_update
    # сравниваем списки компонентов
    from_disk = make_component_dict(parsed_form.queries)
    from_db = make_component_dict(form.components)
    # добавляем форму на обновление
    # summary ...
    for key in from_disk:
        if key not in from_db:
            # отправляем компонент на создание
            pass
        else:
            if from_db[key].crc32 != from_disk[key].crc32:
                # отправляем компонент на обновление
                pass
            del from_db[key]
    for key in from_db:
        # удаляем компоненты, не имеющие соответствия на диске
        pass    
    return summary

def sync_application(application):
    summary = get_new_sync_summary()
    if not os.path.exists(application.path):
        # добавить арм на удаление
        return summary
    project = DelphiProject(application.path)
    application.last_update = project.last_update
    # добавить арм на обновление
    # summary ...
    from_disk = make_component_dict(project.forms)
    from_db = make_component_dict(application.forms)
    for key in from_disk:
        if key not in from_db:
            # отправляем форму на создание
            pass
        else:
            # подумать про дату обновления и дату синхронизации
            # отправляем форму на обновление
            pass
            del from_db[key]
    for key in from_db:
        # удаляем формы, не имеющие соответствия на диске
        pass    
    return summary

def seed_first():
    to_add = []
    bad_forms = {}
    connections = {}
    project_info = json.load(open('term.json', 'r', encoding="utf-8"))
    path = project_info["path"]
    name = project_info["name"]
    proj = DelphiProject(path)    
    term_app = Application(name=name, path_to_dproj=path, last_update=proj.last_update)
    to_add.append(term_app)
    for f in proj.forms:
        try:
            print(f"Обработка {os.path.split(f)[-1]}")
            parsed_form = DelphiForm(f)
            parsed_form.read_dfm()            
            new_form = Form(
                name=os.path.split(f)[-1],
                path = f,
                alias=parsed_form.alias,
                last_update=parsed_form.last_update,
                application=term_app)            
            to_add.append(new_form)
            to_add.append(Link(from_node=term_app, to_node=new_form))
            for comp in parsed_form.get_db_components():
                if isinstance(comp, DelphiQuery):
                    if comp.connection is not None and comp.connection not in connections:
                        connections[comp.connection] = ClientConnection(
                            name=comp.connection,
                            application=term_app,
                            database_name=''
                        )
                        to_add.append(connections[comp.connection])
                    new_component = ClientQuery(
                        name=comp.name,
                        connection=connections[comp.connection],
                        form=new_form,
                        sql=comp.sql,
                        component_type=comp.type,
                        last_update=parsed_form.last_update,
                        crc32=comp.crc32
                    )                    
                    to_add.append(new_component)
                    to_add.append(Link(from_node=new_form, to_node=new_component))
                else:
                    if comp.name not in connections:
                        connections[comp.name] = ClientConnection(
                            name=comp.full_name,
                            application=term_app,
                            database_name=comp.database,
                        )
                        to_add.append(connections[comp.name])
                    else:
                        print(f"Connection found")
                        connections[comp.name].database_name = comp.database
                        print(f"Connection modified")

        except Exception as e:
            bad_forms[f] = str(e)
    session.add_all(to_add)
    session.flush()
    json.dump(bad_forms, open("badforms.json", 'w', encoding="utf-8"), indent=4, ensure_ascii=False)

def show_results():
    for row in session.query(Link).all():
        print(row)

seed_first()
show_results()

