import re
from .models import Edge, Database, DBScript, ClientQuery, DatabaseObject
from sqlalchemy.sql import text
from sqlalchemy import or_
import logging


def analize_links(session, conn):
    # нужно проверять при синхронизации скриптов, не сломаны ли они
    scripts = session.query(DBScript).filter(or_(DBScript.last_revision == None, DBScript.last_update > DBScript.last_revision)).all()
    components = session.query(ClientQuery).filter(or_(ClientQuery.last_revision == None, ClientQuery.last_update > ClientQuery.last_revision)).all()
    grab_all = (len(components) > 0) # or there is script.is_broken == True
    #objects_to_check = session.query(DatabaseObject).all()
    res = {}
    has_broken_scripts = False
    for script in scripts:
        query = text(
            """
            SELECT distinct referenced_id FROM
            sys.dm_sql_referenced_entities(:obj_long_name,'OBJECT')
            WHERE referenced_id is not NULL""")
        try:
            system_references = conn.execute(query, obj_long_name=script.long_name)
            res[script.long_name] = system_references
        except Exception as e:
            has_broken_scripts = True
            #script.is_broken = True
            logging.warning(f"Скрипт {script.long_name} сломан, зависимости не читаются")
    """if has_broken_scripts:
        session.commit()"""
    query = text(
        """
        SELECT distinct referenced_id FROM
        sys.dm_sql_referenced_entities('dbo.x_QueriesBankSIUD','OBJECT')
        WHERE referenced_id is not NULL""")
    record = conn.execute(query)

    print("-------------------------------")
    for key in res:
        for row in res[key]:
            print(row)
    print("-------------------------------")
    
    
