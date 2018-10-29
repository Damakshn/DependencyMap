import datetime
import json
from models import *
from delphitools import DelphiProject, DelphiForm, DelphiQuery, DelphiConnection
import os.path

NOW = datetime.datetime.now()

def seed_first():
    to_add = []
    bad_forms = {}
    connections = {}
    project_info = json.load(open('term.json', 'r', encoding="utf-8"))
    path = project_info["path"]
    name = project_info["name"]
    proj = DelphiProject(path)    
    term_app = Application(name=name, path_to_dproj=path, last_update=proj.last_update)
    to_add.append(term_app)
    for f in proj.forms:
        try:
            print(f"Обработка {os.path.split(f)[-1]}")
            parsed_form = DelphiForm(f)
            parsed_form.read_dfm()            
            new_form = Form(
                name=os.path.split(f)[-1],
                path = f,
                alias=parsed_form.alias,
                last_update=parsed_form.last_update,
                application=term_app)            
            to_add.append(new_form)
            to_add.append(Link(from_node=term_app, to_node=new_form))
            for comp in parsed_form.get_db_components():
                if isinstance(comp, DelphiQuery):
                    if comp.connection is not None and comp.connection not in connections:
                        connections[comp.connection] = ClientConnection(
                            name=comp.connection,
                            application=term_app,
                            database_name=''
                        )
                        to_add.append(connections[comp.connection])
                    new_component = ClientQuery(
                        name=comp.name,
                        connection=connections[comp.connection],
                        form=new_form,
                        sql=comp.sql,
                        component_type=comp.type,
                        last_update=parsed_form.last_update,
                        crc32=comp.crc32
                    )                    
                    to_add.append(new_component)
                    to_add.append(Link(from_node=new_form, to_node=new_component))
                else:
                    if comp.name not in connections:
                        connections[comp.name] = ClientConnection(
                            name=comp.full_name,
                            application=term_app,
                            database_name=comp.database,
                        )
                        to_add.append(connections[comp.name])
                    else:
                        print(f"Connection found")
                        connections[comp.name].database_name = comp.database
                        print(f"Connection modified")

        except Exception as e:
            bad_forms[f] = str(e)
    session.add_all(to_add)
    session.flush()
    json.dump(bad_forms, open("badforms.json", 'w', encoding="utf-8"), indent=4, ensure_ascii=False)

def show_results():
    for row in session.query(Link).all():
        print(row)

seed_first()
show_results()

