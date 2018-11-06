import datetime
import json
from models import Application, Form, ClientConnection, ClientQuery, Link, SessionDPM
from delphitools import DelphiProject, DelphiForm, DelphiQuery, DelphiConnection
import os.path


class SyncSummary:
    """
    Каталог синхронизируемых объектов.

    Используется как временный буфер, куда складываются будущие изменения.
    Объекты, попадая в каталог, делятся на 3 категории: создаваемые, удаляемые и обновляемые.

    Процесс синхронизации с исходниками сложен и подвержен ошибкам, поэтому необходим
    учёт всех изменений до того, как они записаны в базу; это позволяет управлять синхронизацией,
    останавливая её в случае ошибки или выводя пользователю предпреждающие сообщения.
    """
    def __init__(self):
        self.empty = True

    @property
    def empty(self):
        return True

    def send_to_create(self, orm_object):
        """
        Помещает ORM-объект в каталог на вставку в таблицу базы данных.
        """
        self.empty = False

    def send_to_update(self, data):
        """
        Помещает ORM-объект в каталог на обновление.
        """
        self.empty = False

    def send_to_delete(self, data):
        """
        Помещает ORM-объект в каталог на удаление.
        """
        self.empty = False

    @property
    def description(self):
        """
        Состав применяемых изменений - что будет создано/обновлено/удалено.
        """
        return f""

    def apply_changes(self, session):
        pass

    def merge_with(self, other):
        """
        Вливает в текущий каталог содержимое другого каталога.
        """
        pass

    def forms_to_create(self):
        pass

    def forms_to_update(self):
        pass


session = SessionDPM()
    
def make_named_dict(components_list, key):
    """
    Преобразует список компонентов (выбранных из базы или полученных
    после парсинга файла формы) в словарь вида "идентификатор_компонента": компонент.
    В качестве идентификатора выбирается значение поля key.
    """
    result = {}
    for component in components_list:
        result[component[key]] = component
    return result

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
    return True

def update_subordinate_member(obj_from_disk, obj_from_db):
    """
    Обновляет данные ORM-объекта, используя информацию, взятую из исходников.

    Способ обновления зависит от класса обновляемого объекта.

    Изменяются только те данные, которые относятся непосредственно к обновляемому объекту,
    зависимости обновляемого объекта метод не трогает.
    """
    if isinstance(obj_from_db, Form):
        obj_from_db.last_update = obj_from_disk.last_update
    elif isinstance(obj_from_db, ClientQuery):
        obj_from_db.sql = obj_from_disk.sql
    elif isinstance(obj_from_db, ClientConnection):
        obj_from_db.database_name = obj_from_disk.database_name

def create_subordinate_member_from_source(source_object):
    """
    Создаёт новый ORM-объект, используя информацию из исходников.

    Класс создаваемого объекта подбирается исходя из класса исходного объекта.
    """
    if isinstance(source_object, DelphiConnection):
        return None
    elif isinstance(source_object, DelphiForm):
        return None
    elif isinstance(source_object, DelphiQuery):
        return None
    else:
        raise Exception("Этот класс не поддерживается.")

def sync_subordinate_members(original_items, db_items, **refs) -> SyncSummary:
    """
    Сопоставляет 2 словаря объектов: актуальные объекты в исходниках на диске
    и объекты ORM, взятые из БД.

    Метод определяет, какие объекты должны быть созданы, изменены или удалены.
    Возвращает каталог, содержащий объекты ORM, поделённые на 3 соответствующие категории.

    Третий параметр - ссылки на другие ORM-модели, которые нужно прикрепить при создании/обновлении.
    """
    summary = SyncSummary()
    for item in original_items:
        # объект есть на диске, но отсутствует в БД - создать
        if item not in db_items:
            summary.send_to_create(
                db_items[item].__class__.create_from(original_items[item], **refs)
            )
        # объект есть и там, и там - сравнить и обновить, затем исключить объект из словаря
        elif item in db_items and needs_update(original_items[item], db_items[item]):
            db_items[item].update_from(original_items[item], **refs)
            summary.send_to_update(db_items[item])
            del db_items[item]
    # в перечне объектов, сохранённых в базе остались только те, которые
    # не имеют оригинала в исходниках, их надо удалить
    for item in db_items:
        summary.send_to_delete(db_items[item])
    return summary

def sync_form(form, connections):
    """
    Синхронизирует отдельно взятую форму.
    """
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
    # сопоставляем списки компонентов
    original_components = make_named_dict(parsed_form.queries, "name")
    db_components = make_named_dict(form.components, "name")
    refs = {"form": form, "connections": connections}
    components_to_sync = sync_subordinate_members(original_components, db_components, **refs)
    # результат синхронизации вливаем в общий каталог
    summary.merge_with(components_to_sync)
    # добавляем форму на обновление
    form.update_from(parsed_form)
    summary.send_to_update(form)
    return summary

def sync_form_components(original_form, db_form):
    """
    Синхронизирует список компонентов на форме.
    """
    pass

def sync_application(app):
    """
    Синхронизирует данные АРМа в базе с исходниками на диске.
    Если файл проекта не найден, то информация из БД будет удалена.

    Синхронизация не выполняется, если в проекте не было изменений.

    Метод парсит все формы, входящие в проект, чтобы собрать все соединения
    с базами, затем синхронизируются данные форм.
    """
    summary = SyncSummary()
    if not os.path.exists(app.path):
        summary.send_to_delete(app)
        return summary
    project = DelphiProject(app.path)
    if app.last_update == project.last_update:
        return summary
    app.last_update = project.last_update
    summary.send_to_update(app)
    # разбираем оригиналы всех форм, входящих в проект
    parsed_forms = [DelphiForm(form["path"]) for form in project.forms]
    # формируем список соединений арма с базами
    connection_pool = []
    for form in parsed_forms:
        connection_pool.extend(form.connections)
    original_connections = make_named_dict(connection_pool, "name")
    repl_connections = make_named_dict(app.connections, "name")
    connections_to_sync = sync_subordinate_members(original_connections, repl_connections, app=app)
    summary.merge_with(connections_to_sync)
    # ToDo get persistent connections from summary
    # сопоставляем списки форм, входящих в проект
    original_forms = make_named_dict(parsed_forms, "path")
    repl_forms = make_named_dict(app.forms, "path")
    refs = {"app": app, "connections":connection_pool}
    forms_to_sync = sync_subordinate_members(original_forms, repl_forms, **refs)
    summary.merge_with(forms_to_sync)
    forms_for_sync = []
    forms_for_sync.extend(summary.forms_to_create)
    forms_for_sync.extend(summary.forms_to_update)
    for form in forms_for_sync:
        sync_form(form, connection_pool)
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

