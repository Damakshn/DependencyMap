"""
Функции и классы общего назначения, используемые для получения информации
об объектах информационной системы или для их синхронизации с 
нодами графа зависимостей.
"""
from typing import List, Dict
from dpm.models import (
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
from .delphi_classes import DelphiProject, DelphiForm, DelphiQuery, DelphiConnection
import sync.original_models as original_models

def get_remaining_objects(session, cls) -> List[Node]:
    """
    Возвращает список объектов заданного класса в сессии, оставшихся 
    после удаления в методе sync_subordinate_members 
    (то есть список новых и модифицированных объектов).
    """
    result = [item for item in session.dirty if isinstance(item, cls)]
    result.extend([item for item in session.new if isinstance(item, cls)])
    return result

def sync_subordinate_members(originals, nodes, session, **refs):
    """
    Самый главный метод всей синхронизации.

    Сопоставляет 2 списка объектов: актуальные объекты в исходниках на диске
    и их реплики в виде объектов ORM, взятых из БД.

    Метод определяет, какие объекты должны быть созданы, изменены или удалены.

    Четвёртый параметр - ссылки на другие ORM-модели, которые нужно 
    прикрепить при создании/обновлении.
    """
    # превращаем поданные на вход списки в словари, чтобы их было проще сравнивать поэлементно
    original_dict = make_named_dict(originals)
    node_dict = make_named_dict(nodes)
    for item in original_dict:
        # объект есть на диске, но отсутствует в БД - создать
        if item not in node_dict:
            new_orm_object = make_node_from(original_dict[item], **refs)
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
        elif item in node_dict and needs_update(original_dict[item], node_dict[item]):
            node_dict[item].update_from(original_dict[item], **refs)
            del node_dict[item]
    # в перечне объектов, лежащих сейчас в базе, остались только те, которые
    # не имеют оригинала в исходниках, их надо удалить
    for item in node_dict:
        session.delete(node_dict[item])

def make_named_dict(component_list) -> Dict:
    """
    Вспомогательный метод, упрощающий отсев объектов синхронизации.

    Преобразует список объектов (выбранных из базы или полученных
    из исходников) в словарь вида "идентификатор_компонента": компонент.

    Имя поля-идентификатора зависит от класса упаковываемых объектов 
    (определяется свойством key_field). 

    Если на входе будет пустой список, на выходе будет пустой словарь.
    """
    result = {}
    if component_list:
        key = component_list[0].__class__.key_field()
        for component in component_list:
            result[getattr(component, key)] = component
    return result

def make_node_from(original, **refs) -> Node:
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

def needs_update(original, node) -> bool:
    """
    Сравнивает реализацию объекта из исходников на диске с реализацией
    в виде ORM-объекта, взятой из БД.

    Критерий сравнения - либо дата обновления, либо контрольная сумма, 
    в зависимости от наличия того или иного атрибута.
    Возвращает True, если объект из базы устарел и должен быть обновлён.
    """
    if hasattr(node, "last_update") and hasattr(original, "last_update"):
        return node.last_update < original.last_update
    elif hasattr(node, "crc32") and hasattr(original, "crc32"):
        return node.crc32 != original.crc32
    else:
        return True
