"""
Функции и классы общего назначения, используемые для получения информации
об объектах информационной системы или для их синхронизации с 
нодами графа зависимостей.
"""
from typing import List, Dict
from dpm.models import (
    Application,
    Form,
    ClientQuery,
    Edge,
    Node,
    DBTable,
    DBScalarFunction,
    DBTableFunction,
    DBView,
    DBStoredProcedure,
    DBTrigger
    )
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

def sync_subordinate_members(originals: Dict, node_class, nodes: Dict, session, parent):
    """
    Самый главный метод всей синхронизации.

    Сопоставляет 2 словаря объектов: актуальные объекты в исходниках на диске
    или в боевой базе и их реплики в виде объектов ORM, взятых из базы DPM.

    Метод определяет, какие объекты должны быть созданы, изменены или удалены.

    Аргументы:

    originals - оригиналы объектов, прочитанные из исходников Delphi или из БД
    информационной системы;

    node_class - ссылка на модель данных в системе DPM, используется для создания нового экземпляра;

    nodes - ноды графа зависимостей, взятые из БД DPM;

    session - объект-сессия для работы с базой;
    """
    for object_key in originals:
        # объект есть на диске, но отсутствует в БД - создать
        if object_key not in nodes:
            new_node = node_class.create_from(originals[object_key], parent)
            session.add(new_node)
        # объект есть и там, и там - сравнить и обновить
        elif object_key in nodes and needs_update(originals[object_key], nodes[object_key]):
            nodes[object_key].update_from(originals[object_key])
    for object_key in nodes:
        if object_key not in originals:
            session.delete(nodes[object_key])

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

