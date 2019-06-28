import re
from .models import Edge, DBScript, ClientQuery, DatabaseObject
from sqlalchemy.sql import text
from sqlalchemy import or_
import logging
import itertools
from sqlalchemy.exc import ProgrammingError, DBAPIError


def analize_links(session, conn):
    components = session.query(ClientQuery).filter(or_(ClientQuery.last_revision == None, ClientQuery.last_update > ClientQuery.last_revision)).all()
    all_objects = session.query(DatabaseObject).filter(or_(DBScript.last_revision == None, DBScript.last_update > DBScript.last_revision)).all()
    for obj in all_objects:
        try:
            query = text("select referencing_id from sys.dm_sql_referencing_entities(:long_name, 'OBJECT')")
            refs = conn.execute(query, long_name=obj.long_name)
            ids = [row[0] for row in refs]
            scripts = [obj for obj in all_objects if obj.database_object_id in ids and isinstance(obj,DBScript)]
            home_regexp = re.compile(obj.get_regexp_for_home_db())
            foreign_regexp = re.compile(obj.get_regexp_for_foreign_db())
            for script in itertools.chain(scripts, components):
                if obj.database == script.database:
                    regexp = home_regexp  
                else:
                    regexp = foreign_regexp
                search_result = re.search(regexp, script.sql)
                # ToDo отрезать триггеры, у них не должно в принципе метода формирования регулярки
                # ToDo изменить способ работы с компонентами хранимых процедур, у них должно быть поле proc_name или как-то так
                if search_result is not None and len(search_result.groupdict()) > 0:
                    d = search_result.groupdict()
                    edge = Edge(from_node=script,to_node=obj)
                    for key in d:
                        if d[key] is not None:
                            setattr(edge, key, True)
                    session.add(edge)
                    logging.info(f"Связь {d} {script.name} -> {obj.name}")
        except (DBAPIError, ProgrammingError) as e:
            logging.warning(f"Ошибка: {e}")
    session.commit()
        
 