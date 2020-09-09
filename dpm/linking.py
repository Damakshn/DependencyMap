import re
from .models import Edge, DBScript, ClientQuery, DatabaseObject, DBTrigger
from sqlalchemy.sql import text
from sqlalchemy import or_
import logging
import itertools
from sqlalchemy.exc import ProgrammingError, DBAPIError


def analize_links(session, conn):
    components = session.query(ClientQuery).filter(
        or_(
            ClientQuery.last_revision is None,
            ClientQuery.last_update > ClientQuery.last_revision
        )
    ).all()
    all_objects = session.query(DatabaseObject).filter(
        or_(
            DBScript.last_revision is None,
            DBScript.last_update > DBScript.last_revision
        )
    ).all()
    script_name = ""
    obj_name = ""
    for obj in all_objects:
        # ToDo отрезать триггеры, у них не должно в принципе метода формирования регулярки
        if isinstance(obj, DBTrigger):
            continue
        try:
            obj_name = obj.name
            query = text("select referencing_id from sys.dm_sql_referencing_entities(:long_name, 'OBJECT')")
            refs = conn.execute(query, long_name=obj.long_name)
            ids = [row[0] for row in refs]
            scripts = [
                obj
                for obj in all_objects
                if obj.database_object_id in ids and isinstance(obj, DBScript)
            ]
            # ToDo изменить способ работы с компонентами хранимых процедур, у них должно быть поле proc_name
            home_regexp = re.compile(obj.get_regexp_for_home_db())
            foreign_regexp = re.compile(obj.get_regexp_for_foreign_db())
            for script in itertools.chain(scripts, components):
                script_name = script.name
                if obj.database == script.database:
                    regexp = home_regexp
                else:
                    regexp = foreign_regexp
                edge_template = {}
                for match in regexp.finditer(script.sql):
                    edge_template[match.lastgroup] = True
                if len(edge_template) > 0:
                    edge = Edge(source=script, dest=obj)
                    for key in edge_template:
                        setattr(edge, key, True)
                    session.add(edge)
                    logging.info(f"Связь {edge_template} {script.name} -> {obj_name}")
        except (DBAPIError, ProgrammingError, KeyError) as e:
            if isinstance(e, KeyError):
                print(f"KeyError - {script_name}")
            logging.warning(f"Ошибка: {e}")
