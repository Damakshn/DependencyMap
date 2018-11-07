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
        # Для раскладывания синхронизируемых объектов по категориям.
        self.update = {}
        self.delete = {}
        self.create = {}
        """
        При формировании каталога эти словари заполняются так:
            self.update = {"Form": [obj1, obj2], "Application": [obj3]}
            self.delete = {"ClientQuery": [obj4, obj5]}
            т.е. в качестве ключей словаря используются имена классов сохраняемых объектов.
        """
    
    def __save_to(self, category_name, obj):
        """
        Сохраняет объект в выбранную категорию.
        В качестве ключа используется имя класса сохраняемого объекта.
        Выделяет место внутри категории, если необходимо.
        """
        category = getattr(self, category_name)
        key = obj.__class__.__name__
        if key not in category:
            category[key] = []
        category[key].append(obj)
        

    def send_to_create(self, orm_object):
        """
        Помещает ORM-объект в каталог на вставку в таблицу базы данных.
        """
        self.__save_to("create", orm_object)
        self.empty = False

    def send_to_update(self, orm_object):
        """
        Помещает ORM-объект в каталог на обновление.
        """
        self.__save_to("update", orm_object)
        self.empty = False

    def send_to_delete(self, orm_object):
        """
        Помещает ORM-объект в каталог на удаление.
        """
        self.__save_to("delete", orm_object)
        self.empty = False
    
    def get_deleted_objects(self, cls):
        """
        Возвращает список объектов на удаление.

        Если указан класс, то список будет отфильтрован по этому классу.
        """
        return self.__get_objects_in_category("delete", cls)
    
    def get_updated_objects(self, cls):
        """
        Возвращает список объектов на обновление.

        Если указан класс, то список будет отфильтрован по этому классу.
        """
        return self.__get_objects_in_category("update", cls)
    
    def get_created_objects(self, cls):
        """
        Возвращает список объектов на создание.

        Если указан класс, то список будет отфильтрован по этому классу.
        """
        return self.__get_objects_in_category("create", cls)
    
    def get_persistent_objects(self, cls):
        """
        Возвращает список объектов на обновление и создание.

        Если указан класс, то список будет отфильтрован по этому классу.
        """
        updated = self.__get_objects_in_category("update", cls)
        created = self.__get_objects_in_category("create", cls)
        return created.extend(updated)
    
    def __get_objects_in_category(self, category_name, cls):
        """
        Возвращает список объектов из указанной категории.

        Если класс объектов не указан, то возвращает все объекты в категории,
        иначе - только объекты этого класса.
        """
        cls_name = cls.__name__
        category = getattr(self, category_name)
        if cls_name is None:
            return list(category.values())
        else:
            return category.setdefault(cls_name, [])

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
        for category in ["create", "update", "delete"]:
            other__category = getattr(other, category)
            self__category = getattr(self, category)
            for key in other__category:
                if key not in self__category:
                    self__category[key] = []
                self__category[key].extend(other__category[key])

    def forms_to_create(self):
        pass

    def forms_to_update(self):
        pass


session = SessionDPM()
    
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
    Сопоставляет 2 списка объектов: актуальные объекты в исходниках на диске
    и объекты ORM, взятые из БД.

    Метод определяет, какие объекты должны быть созданы, изменены или удалены.
    Возвращает каталог, содержащий объекты ORM, поделённые на 3 соответствующие категории.

    Третий параметр - ссылки на другие ORM-модели, которые нужно прикрепить при создании/обновлении.
    """
    summary = SyncSummary()
    # превращаем поданные на вход списки в словари, чтобы их было проще сравнивать поэлементно
    originals = make_named_dict(original_items)
    replicas = make_named_dict(db_items)
    for item in originals:
        # объект есть на диске, но отсутствует в БД - создать
        if item not in replicas:
            summary.send_to_create(
                replicas[item].__class__.create_from(originals[item], **refs)
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
    # синхронизируем компоненты на форме
    refs = {"form": form, "connections": connections}
    # todo добавить поля queries и connections классу DelphiForm
    components_to_sync = sync_subordinate_members(parsed_form.queries, form.components, **refs)
    # результат синхронизации вливаем в общий каталог
    summary.merge_with(components_to_sync)
    # добавляем форму на обновление
    form.update_from(parsed_form)
    summary.send_to_update(form)
    return summary

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
    # формируем список соединений арма с базами и синхронизируем его
    connection_pool = []
    for form in parsed_forms:
        connection_pool.extend(form.connections)
    connections_to_sync = sync_subordinate_members(connection_pool, app.connections, app=app)
    summary.merge_with(connections_to_sync)
    # теперь connection_pool - это словарь
    connection_pool = make_named_dict(summary.get_persistent_objects(ClientConnection))
    # сопоставляем списки форм, входящих в проект
    refs = {"app": app, "connections":connection_pool}
    forms_to_sync = sync_subordinate_members(parsed_forms, app.forms, **refs)
    summary.merge_with(forms_to_sync)
    forms_for_sync = summary.get_persistent_objects(Form)
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

