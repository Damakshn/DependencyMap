from flashtext import KeywordProcessor
from .models import Link, Database, SQLQuery

def __is_relevant(match, text):
    """
    Осуществляет отсев результатов поиска:
    * не пропускает результаты, начинающиеся не с пробела;
    * отделяет спорные совпадения select от delete
    """
    # отбрасываем результаты, начинающиеся не с пробела
    # match[1] - позиция в тексте, с которой начинается совпадение
    space_before = (text[match[1]-1] == " ")
    # отделяем спорные совпадения select & delete
    is_clear = ((match[0] != "contestive_select") or 
        ((match[0] == "contestive_select") and text[match[1]-12:match[1]] != "delete from "))
    return all([space_before, is_clear])

def build_links_for(dbnode, session):
    """
    Метод строит входящие связи для выбранного объекта базы данных.

    Связь создаётся в том случае, если имя объекта упомянуто в исходниках 
    какого-нибудь запроса.

    Поиск проводим в 2 этапа - сначала в той же базе, к которой 
    относится исследуемый объект, затем последовательно во всех остальных.
    Это нужно для того, чтобы отличать объекты с одинаковыми именами из разных баз,
    например db1.dbo.some_table и db2.dbo.some_table. Если таблица some_table из базы 
    db1 использована в запросе, выполняемом в контексте базы db2 (например, в хранимой
    процедуре), то к ней нужно обращаться строго по полному имени - база.схема.имя.
    Поиск в 2 прохода позволяет избежать ситуации, когда по короткому имени идентифицирован
    не тот объект.

    Для поиска соответствий исходники всех запросов соединяются в один большой кусок текста,
    в котором flashtext ищет совпадения. Для точной идентификации удаляются соответствия,
    у которых перед совпадением отсутствует пробел (flashtext не поддерживает поиск по шаблону).
    """
    # заряжаем flashtext ключевыми словами
    processor = KeywordProcessor()
    processor.add_keywords_from_dict(dbnode.get_keywords())
    # получаем все запросы "родной" базы объекта
    home_db_queries = session.query(SQLQuery).filter_by(database_id=dbnode.database_id)
    # склеиваем все исходники в единый текст, запоминаем границы запросов
    boundaries = [0]
    query_mapping = {}
    total_length = 0
    for query in home_db_queries:
        # +1 к длине за перенос строки, который отделяет один запрос от другого
        total_length = total_length + len(query.sql) + 1
        boundaries.append(total_length)
        query_mapping[total_length] = {
            "query": query,
            "link": None
        }
    all_sql = "\n".join([query.sql for query in home_db_queries])
    search_results = processor.extract_keywords(all_sql, span_info=True)
    search_results = [match for match in search_results if __is_relevant(match, all_sql)]
    # строим связи
    for word, start, end in search_results:
        # смотрим, в каком запросе нашлось совпадение
        for i in range(1, len(boundaries)):
            if start < boundaries[i] and start >= boundaries[i-1]:
                # если связи нет - создаём, если есть - ставим True в нужное поле
                if query_mapping[boundaries[i]]["link"] is None:
                    query_mapping[boundaries[i]]["link"] = Link(
                        from_node=query_mapping[boundaries[i]]["query"],
                        to_node=dbnode,
                        call=(word == "exec"),
                        select=(word in ("select", "contestive_select")),
                        insert=(word == "insert")
                        update=(word == "update")
                        delete=(word == "delete")
                        truncate=(word == "truncate")
                        drop=(word == "drop")
                    )
                    session.add(query_mapping[boundaries[i]]["link"])
                else:
                    field = word if word not in ("select", "contestive_select") else "select"
                    query_mapping[boundaries[i]]["link"][field] = True
                break    