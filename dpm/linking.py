import re
from .models import Link, Database, SQLQuery
from sqlalchemy.sql import text

"""
Последовательность действий при построении ссылок:
	Получить referencing_nodes и создать сессию
	Подгрузить referenced_nodes, исходя из состава referencing_nodes;
	Пройти по referencing_nodes, клепая ссылки;
	Отдать созданные ссылки либо сразу отправить их в БД;

Анализ текста для ноды из referencing_nodes
	если мы строим ссылки для компонента - перебираем referenced_nodes
	если мы строим ссылки для скрипта - перебираем его зависимости и прицельно по object_id достаём ноды из referenced_nodes
	...
	тут можно создать объект-итератор!
	проверяем связь между нодой из referenced_nodes и нодой из referencing_nodes -> возвращаем ссылки

Проверка связей между нодами
	нам понадобится список возможных атрибутов, состоящий из ['SQL','ModifySQL','InsertSQL','DeleteSQL'] и т.п.
	если у обеих нод одинаковые базы
		у ноды из referenced_nodes достаём home_db_regex, кладём в regex
	если базы разные
		у ноды из referenced_nodes достаём foreign_db_regex, кладём в regex
	перебираем список атрибутов
		если у ноды в referencing_nodes есть такой атрибут (hasattr)
			достаём его значение (getattr) в text
		проверяем text с помощью regex
		разбираем результат проверки -> возвращаем ссылки
"""

class ReferenceBuilder:
    referenced_nodes = {}
    referencing_nodes = {}
    session = None

    def __init__(self, referencing_nodes, session):
        self.referencing_nodes = referencing_nodes
        self.session = session

    def populate_referenced_entities(self):
        """
        Если в referencing_nodes есть хотя бы один компонент, не являющийся процедурой, то тащим все DatabaseObject'ы и заканчиваем;
	    Иначе перебираем referencing_nodes и дополняем referenced_nodes списком его зависимостей
        """
        for node_id in self.referencing_nodes:
            if isinstance(self.referencing_nodes[node_id], DelphiDBComponent) and not isinstance(self.referencing_nodes[node_id], StoredProcComponent):
                # ToDo добавить подгребание всех DatabaseObject
                return
        for node_id in self.referencing_nodes:
            if isinstance(self.referencing_nodes[node_id], DBScript):
                self.referenced_nodes.update(self.referencing_nodes[node_id].references)

    def build_links_for_single_node(self, node):
        """
        если попалась TADOStoredProc - прицельно выцепить нужную процедуру из базы и создать ссылку;
	    если другой компонент или скрипт - юзаем hasattr/getattr, чтобы достать текст(ы) и проанализировать
	    вернуть ссылки
        """
        if isinstance(node, StoredProcComponent):
            return self.build_links_for_storedproc(node)
        else:
            return self.build_links_for_script(node)
    
    def build_links_for_storedproc(self, spcomponent):
        """
        прицельно выцепить нужную процедуру из базы и создать ссылку;
        """
        pass
    
    def build_links_for_script(self, node):
        """
        если мы строим ссылки для компонента - перебираем referenced_nodes
        если мы строим ссылки для скрипта - перебираем его зависимости и прицельно по object_id достаём ноды из referenced_nodes
        ...
        тут можно создать объект-итератор!
        проверяем связь между нодой из referenced_nodes и нодой из referencing_nodes -> возвращаем ссылки
        """
        objects_to_check = []
        result = []
        if isinstance(node, DelphiDBComponent):
            objects_to_check = self.referenced_nodes
        else:
            objects_to_check = node.references # ToDo dict compr
        for object_id in objects_to_check:
            result.append(self.find_node_usages_in_script(node, objects_to_check[object_id]))
    
    def find_node_usages_in_script(self, script, node):
        """
        нам понадобится список возможных атрибутов, состоящий из ['SQL','ModifySQL','InsertSQL','DeleteSQL'] и т.п.
        если у обеих нод одинаковые базы
            у ноды из referenced_nodes достаём home_db_regex, кладём в regex
        если базы разные
            у ноды из referenced_nodes достаём foreign_db_regex, кладём в regex
        перебираем список атрибутов
            если у ноды в referencing_nodes есть такой атрибут (hasattr)
                достаём его значение (getattr) в text
            проверяем text с помощью regex
            разбираем результат проверки -> возвращаем ссылки
        """
        result = []
        # ToDo component class should have a method that returns all it's scripts one by one
        # Referenced builder shouldnt know about possible attributes of scripts
        probable_attributes = ["SQL", "ModifySQL", "InsertSQL", "DeleteSQL"]
        # ToDo compare databases of script and node
        for attr in probable_attributes:
            if hasattr(script, attr):
                text = getattr(script, attr)
                # ToDo make search here
                match = None
                result.append(self.process_search_result(match))
        return result
    
    def process_search_result(self, match):
        pass
            
    def build_links(self):
        self.populate_referenced_entities()

# ------------------------------------------------

def build_links_for(dbnode, session):
    """
    Получаем список скриптов, у которых данный объект находится в зависимостях;
    Получаем список сломанных скриптов;
    Получаем список компонентов Delphi;
    Проходим по всему тому, что получили;
    Если оба объекта из одной базы, используем одну регулярку, если из разных - другую;
    По результатам регулярки создаём входящие связи от скриптов к обрабатываемому объекту;
    По идее, построение связей по регулярке должно быть инкапсулировано в классе ноды, т.к. заранее неизвестно
    какие поля отслеживает регулярка
    """
    pass

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
    query_mapping = {}
    total_length = 0
    for query in home_db_queries:
        # запоминаем диапазоны в тексте, которые занимают запросы
        # получится (0, 1201), (1202, 1500) и т.д.
        # по этим значениям будем определять, в какой запрос мы попали
        boundaries = (total_length, total_length + len(query.sql))
        # +1 к длине за перенос строки, который будет отделять один запрос от другого
        total_length = total_length + len(query.sql) + 1
        query_mapping[boundaries] = {
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
        # не забываем, что ключ query_mapping - это кортеж
        for start, end in query_mapping:
            if pos >= start and pos < end:
                # если связь ещё не создана - создаём, иначе - ставим в True 
                # соответствующее поле уже готового объекта
                if query_mapping[(start, end)]["link"] is None:
                    query_mapping[(start, end)]["link"] = Link(
                        from_node=query_mapping[(start, end)]["query"],
                        to_node=dbnode,
                        exec=(action == "exec"),
                        select=(action == "select"),
                        insert=(action == "insert"),
                        update=(action == "update"),
                        delete=(action == "delete"),
                        truncate=(action == "truncate"),
                        drop=(action == "drop")
                    )
                    session.add(query_mapping[(start, end)]["link"])
                else:
                    #setattr(query_mapping[(start,end)]["link"], match.lastgroup, True)
                    query_mapping[(start,end)]["link"][match.lastgroup] = True
                break
        
    

