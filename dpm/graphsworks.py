import networkx as nx

"""
Этот модуль запрашивает о зависимостях объектов из базы и формирует
на основе полученных данных графы зависимостей объектов.
Полученные таким образом графы могут быть использованы для вывода данных в GUI
или для анализа данных;

При формировании графа все вершины и рёбра должны быть размечены определённым образом:

Атрибуты вершин:
    node_class - содержит класс ORM-модели;
    node_id - id ноды из базы;

Атрибуты рёбер:
    select, insert, update, delete, exec, drop, truncate - ставится True/False, показывает набор операций, которые
    объект A осуществляет с объектом B.

Атрибуты нужны для того, чтобы при обработке графа можно было отличить, например, ноду таблицы
от ноды формы, правильно визуализировать связи нужных типов, дозапрашивать данные из базы по id объекта.
"""

def get_application_graph(app):
    G = nx.DiGraph()
    G.add_node(app.id, label=app.name, node_class=app.__class__.__name__, id=app.id)
    for form in app.forms.values():
        subgraph = get_form_graph(form)
        G.add_nodes_from(subgraph.nodes(data=True))
        G.add_edges_from(subgraph.edges(data=True))
        G.add_edge(app.id, form.id)
            
    return G

def get_form_graph(form):
    G = nx.DiGraph()
    G.add_node(form.id, label=form.alias, node_class=form.__class__.__name__)
    for component in form.components.values():
        subgraph = get_query_graph(component)
        G.add_nodes_from(subgraph.nodes(data=True))
        G.add_edges_from(subgraph.edges(data=True))
        G.add_edge(form.id, component.id)
    return G

def get_query_graph(query):
    G = nx.DiGraph()
    edge_template = ["select", "insert", "update", "delete", "exec", "drop", "truncate"]
    G.add_node(query.id, label=query.name, node_class=query.__class__.__name__, id=query.id)
    for e in query.edges_out:
        # защита от рекурсивных вызовов, где ребро графа циклическое
        if query.id != e.dest.id:
            subgraph = get_query_graph(e.dest)
            G.add_nodes_from(subgraph.nodes(data=True))
            G.add_edges_from(subgraph.edges(data=True))
            G.add_edge(query.id, e.dest.id, **{attr: getattr(e, attr) for attr in edge_template})
    return G

def get_database_graph(database):
    pass

def get_table_graph(tbl):
    pass

def get_script_graph(script):
    pass

"""
def dig_for_dependencies(graph, objects, iteration=1):
    
    #Дополняет граф graph новыми вершинами и рёбрами,
    #идя вглубь по ссылкам зависимостей, идущим от объектов objects.
    
    next_wave = []
    for obj in objects:
        for e in obj.edges_out:
            edge_template = ["select", "insert", "update", "delete", "exec", "drop", "truncate"]
            # если у очередной вершины есть рёбра, которые идут дальше, то включаем её в следующую волну
            # а также
            # блокируем ссылки скриптов на самих себя в результате рекурсивных вызовов
            if len(e.dest.edges_out) > 0 and (e.dest.id != e.sourse.id):
                next_wave.append(e.dest)
            graph.add_node(e.dest.id, label=e.dest.name, id=e.dest.id)
            graph.add_edge(obj.id, e.dest.id, **{attr: getattr(e, attr) for attr in edge_template})
    if len(next_wave) > 0 and iteration <= 30:
        dig_for_dependencies(graph, next_wave, iteration+1)
"""
