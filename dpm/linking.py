import re
from .models import Link, Database, SQLQuery

def build_incoming_links_for(dbnode, session):
    """
    Метод строит входящие связи для выбранного объекта базы данных.

    Связь создаётся в том случае, если имя объекта упомянуто в исходниках 
    какого-нибудь запроса.

    Поиск проводим в 2 этапа - сначала в той же базе, к которой 
    относится исследуемый объект, затем во всех остальных.
    Это нужно для того, чтобы отличать объекты с одинаковыми именами из разных баз,
    например db1.dbo.some_table и db2.dbo.some_table.
    
    Если таблица some_table из базы db1 использована в запросе, выполняемом в 
    контексте базы db2 (например, в хранимой процедуре), то к ней нужно обращаться 
    строго по полному имени - база.схема.имя.

    Поиск в 2 прохода позволяет избежать ситуации, когда по короткому имени идентифицирован
    не тот объект. Также при поиске в других базах перечень ключевых слов меньше, так как
    включает только длинные имена объектов.

    Для поиска соответствий исходники всех запросов соединяются в один большой кусок текста,
    в котором с помощью большого регулярного выражения ищем совпадения.

    Для каждого исследуемого объекта регулярка запрашивается отдельно через метод get_regexp().
    """
    # получаем все запросы "родной" базы объекта
    home_db_queries = session.query(SQLQuery).filter_by(database_id=dbnode.database_id)
    # склеиваем все исходники в единый текст
    # сюда складываем границы запросов, в итоге получится [0, 650, 1433, ...], где каждое
    # число означает позицию в склеенном тексте, где заканчивается очередной запрос.
    boundaries = [0]
    # ToDo мне не нравится переменная query_mapping, надо проверить, можно ли перебирать результат
    # запроса по индексу
    query_mapping = {}
    total_length = 0
    for query in home_db_queries:
        # +1 к длине за перенос строки, который будет отделять один запрос от другого
        total_length = total_length + len(query.sql) + 1
        boundaries.append(total_length)
        query_mapping[total_length] = {
            "query": query,
            "link": None
        }
    all_sql = "\n".join([query.sql for query in home_db_queries])
    regexp = re.compile(dbnode.get_regexp())
    # перебираем совпадения
    for match in regexp.finditer(all_sql):
        # смотрим, какая группа совпала и где в тексте начало совпадения
        pos = match.span()[0]
        action = match.lastgroup
        # по позиции совпадения определяем, в какой запрос мы попали
        for i in range(1, len(boundaries)):
            if pos < boundaries[i] and pos >= boundaries[i-1]:
                # если связь ещё не создана - создаём, иначе - ставим в True 
                # соответствующее поле уже готового объекта
                if query_mapping[boundaries[i]]["link"] is None:
                    query_mapping[boundaries[i]]["link"] = Link(
                        from_node=query_mapping[boundaries[i]]["query"],
                        to_node=dbnode,
                        exec=(action == "exec"),
                        select=(action == "select"),
                        insert=(action == "insert"),
                        update=(action == "update"),
                        delete=(action == "delete"),
                        truncate=(action == "truncate"),
                        drop=(action == "drop")
                    )
                    session.add(query_mapping[boundaries[i]]["link"])
                else:
                    query_mapping[boundaries[i]]["link"][match.lastgroup] = True
                break
        
    

