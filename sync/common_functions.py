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
    DBTable,
    DBScalarFunction,
    DBTableFunction,
    DBView,
    DBStoredProcedure,
    DBTrigger,
    SystemReference)
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


def sync_subordinate_members(originals: Dict, entities: Dict, session, **refs):
    """
    Самый главный метод всей синхронизации.

    Сопоставляет 2 словаря объектов: актуальные объекты в исходниках на диске
    или в боевой базе и их реплики в виде объектов ORM, взятых из базы DPM.

    Метод определяет, какие объекты должны быть созданы, изменены или удалены.

    Четвёртый параметр - ссылки на другие ORM-модели, которые нужно
    прикрепить при создании/обновлении.
    """
    for item in originals:
        # объект есть на диске, но отсутствует в БД - создать
        if item not in entities:
            new_entity = make_new_entity_from(originals[item], **refs)
            session.add(new_entity)
            # если новый объект не является корневым узлом, то
            # нужно создать связь от родительского объекта к нему
            if isinstance(new_entity, Node) and not new_entity.is_root:
                if not isinstance(new_entity, DBTrigger):
                    parent = refs["parent"]
                    session.add(Link(from_node=parent, to_node=new_entity))
                else:
                    parent_table = refs["table"]
                    parent_db = refs["database"]
                    session.add(Link(from_node=parent_table, to_node=new_entity))
                    session.add(Link(from_node=parent_db, to_node=new_entity))
        # объект есть и там, и там - сравнить и обновить, затем исключить объект из словаря
        elif item in entities and needs_update(originals[item], entities[item]):
            entities[item].update_from(originals[item], **refs)
    for item in entities:
        if item not in originals:
            session.delete(entities[item])


def make_new_entity_from(original, **refs) -> Node:
    """
    Создаёт новую системную сущность, класс которой
    соответствует классу оригинала.

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
    # системные зависимости (которые не являются нодами)
    if isinstance(original, original_models.OriginalSystemReferense):
        return SystemReference.create_from(original, **refs)


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

