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
import re

def get_remaining_objects(session, cls) -> List[Node]:
    """
    Возвращает список объектов заданного класса в сессии, оставшихся 
    после удаления в методе sync_subordinate_members 
    (то есть список новых и модифицированных объектов).
    """
    result = [item for item in session.dirty if isinstance(item, cls)]
    result.extend([item for item in session.new if isinstance(item, cls)])
    return result

def sync_subordinate_members(originals: Dict, nodes: Dict, session, **refs):
    """
    Самый главный метод всей синхронизации.

    Сопоставляет 2 словаря объектов: актуальные объекты в исходниках на диске
    и их реплики в виде объектов ORM, взятых из БД.

    Метод определяет, какие объекты должны быть созданы, изменены или удалены.

    Четвёртый параметр - ссылки на другие ORM-модели, которые нужно 
    прикрепить при создании/обновлении.
    """
    for item in originals:
        # объект есть на диске, но отсутствует в БД - создать
        if item not in nodes:
            new_orm_object = make_node_from(originals[item], **refs)
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
        elif item in nodes and needs_update(originals[item], nodes[item]):
            nodes[item].update_from(originals[item], **refs)
            del nodes[item]
    for item in nodes:
        if item not in originals:
            session.delete(nodes[item])

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

def clear_sql(sql: str) -> str:
    """
    Принимает на вход строку, содержащую sql-код и подготавливает её для
    обработки поисковым алгоритмом.

    Весь код приводится к нижнему регистру, удаляются комментарии, 
    лишние пробелы и квадратные скобки; добавляется пробел после запятой.
    """
    def remove_comments(source: str) -> str:
        """
        Вспомогательная функция, удаляющая комментарии из sql.

        По факту, данный код не удаляет комментарии из текста,
        а вырезает текст вокруг комментариев, складывает его в список, 
        который затем склеивается.

        При проходе по файлу функция также отслеживает и кавычки, чтобы 
        не было ошибки при принятии /*, */ или -- в кавычках за комментарий.
        """
        # флаги, говорящие о том, что сейчас мы стоим внутри строчного
        # комментария или внутри строки в кавычках
        in_line = False
        in_string = False
        # уровень вложенности блочного комментария
        in_block = 0
        # позиция, с которой будет копироваться текст за пределами комментов
        start_pos = 0
        # буфер, в который мы будем класть куски текста за пределами комментариев
        chunks = []
        for pos in range(len(source)-1):
            if source[pos] == "'":
                in_string = not (in_block or in_line) and not in_string
            elif source[pos] == "/" and source[pos+1] == "*":
                # сочетание /* имеет значение, если ранее не была открыта
                # строка или строчный комментарий
                in_block = 0 if any([in_string, in_line]) else in_block + 1
                # если это первый блочный комментарий, копируем в буфер весь текст до него
                # если это уже не первое /*, то оно считается уже внутри того
                # комментария, который был открыт первым
                if in_block == 1:
                    chunks.append(source[start_pos:pos])
            elif source[pos] == "*" and source[pos+1] == "/":
                # если нашлась закрывающая скобка блочного комментария, то
                # уменьшаем уровень вложенности на 1;
                # считается только та скобка, которая не закрыта кавычкой или 
                # строчным комментарием;
                # если эта скобка - последняя, то смещаем start_pos к этому месту
                # в тексте, чтобы при копировании перескочить комментарий
                if in_block > 0 and all([not in_string, not in_line]):
                    in_block -= 1
                    if in_block == 0:
                        start_pos = pos + 2
            elif all([source[pos] == "-", source[pos+1] == "-", not in_line, not in_string, not in_block]):
                # отлов строчного комментария - начало
                in_line = True
                chunks.append(source[start_pos:pos])
            elif source[pos] == "\n" and in_line:
                # отлов строчного комментария - конец
                in_line = False
                start_pos = pos + 1
        # закидываем в буфер то, что осталось
        chunks.append(source[start_pos:len(source)])
        return "".join(chunks)
        
    # ----------- основная функция обработки sql -----------
    extra_spaces_and_line_breaks = r"\s+"
    # todo разобраться в lookahead
    comma_no_space = r"(?<=,)(?=[^\s])"
    square_brackets = r"[\[\]]"
    sql = sql.lower()
    sql = remove_comments(sql)
    sql = re.sub(extra_spaces_and_line_breaks, " ", sql)
    sql = re.sub(comma_no_space, " ", sql)
    sql = re.sub(square_brackets, "", sql)
    return sql
