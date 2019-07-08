import networkx as nx
import dpm.models as models
import itertools

"""
Этот модуль запрашивает информацию о зависимостях объектов из базы и формирует
на основе полученных данных графы зависимостей объектов.
Полученные таким образом графы могут быть использованы для вывода данных в GUI
или для анализа данных;

При формировании графа все вершины и рёбра должны быть размечены определённым образом:

Атрибуты вершин:
    node_class - содержит класс ORM-модели;
    node_id - id ноды из базы;

Атрибуты рёбер:
    select, insert, update, delete, exec, drop, truncate, contain, trigger - ставится True/False, показывает набор операций, которые
    объект A осуществляет с объектом B.

Атрибуты нужны для того, чтобы при обработке графа можно было отличить, например, ноду таблицы
от ноды формы, правильно визуализировать связи нужных типов, дозапрашивать данные из базы по id объекта.
"""

def merge_subgraph(graph, subgraph, *edge_attrs, reverse=False):
    graph.add_nodes_from(subgraph.nodes(data=True))
    graph.add_edges_from(subgraph.edges(data=True))
    for attr in edge_attrs:
        # соединяем ребром центральные элементы, относительно которых построены графы
        if reverse:
            from_node = subgraph.graph["central_node_id"]
            to_node = graph.graph["central_node_id"]
        else:
            from_node = graph.graph["central_node_id"]
            to_node = subgraph.graph["central_node_id"]
        graph.add_edge(from_node, to_node, **{attr: True})

def build_graph_up(node):
    """
    Строит граф объектов, зависимых от заданного, рекурсивно двигаясь вверх по иерархии объектов (изнутри наружу).
    """
    G = nx.MultiDiGraph(central_node_id=node.id)
    G.add_node(node.id, label=node.label, node_class=node.__class__.__name__, id=node.id)
    if isinstance(node, models.Database) or isinstance(node, models.Application):
        return
    elif isinstance(node, models.Form):
        for app in node.applications:
            G.add_node(app.id, label=app.label, node_class=app.__class__.__name__, id=app.id)
            G.add_edge(app.id, node.id, contain=True)
    elif isinstance(node, models.ClientQuery):
        subgraph = build_graph_up(node.form)
        merge_subgraph(G, subgraph, "contain", reverse=True)
    else:
        edge_template = ["calc", "select", "insert", "update", "delete", "exec", "drop", "truncate"]
        for e in node.edges_in:
            # защита от рекурсивных вызовов, где ребро графа циклическое
            if e.sourse.id == e.dest.id:
                continue
            subgraph = build_graph_up(e.sourse)
            merge_subgraph(G, subgraph, *[attr for attr in edge_template if getattr(e,attr,False) == True], reverse=True)
    return G

def build_graph_in_depth(node):
    """
    Строит граф объектов, от которых зависит заданный объект, рекурсивно копая вглубь.
    """
    G = nx.MultiDiGraph(central_node_id=node.id)
    G.add_node(node.id, label=node.label, node_class=node.__class__.__name__, id=node.id)
    # не используем поле scripts, так как оно включает в себя триггеры, а их мы подберём, строя графы для таблиц
    if isinstance(node, models.Database):
        for obj in itertools.chain(
            node.tables.values(), 
            node.scalar_functions.values(),
            node.table_functions.values(),
            node.procedures.values(),
            node.views.values()
        ):
            subgraph = build_graph_in_depth(obj)
            merge_subgraph(G, subgraph, "contain")
    elif isinstance(node, models.Application):
        for form in node.forms.values():
            subgraph = build_graph_in_depth(form)
            merge_subgraph(G, subgraph, "contain")
    elif isinstance(node, models.Form):
        for component in node.components.values():
            subgraph = build_graph_in_depth(component)
            merge_subgraph(G, subgraph, "contain")
    elif isinstance(node, models.DBTable):
        for trigger in node.triggers.values():
            subgraph = build_graph_in_depth(trigger)
            merge_subgraph(G, subgraph, "trigger")
    else:
        edge_template = ["calc", "select", "insert", "update", "delete", "exec", "drop", "truncate"]
        for e in node.edges_out:
            # защита от рекурсивных вызовов, где ребро графа циклическое
            if e.sourse.id == e.dest.id:
                continue
            if isinstance(e.sourse, models.DBTrigger) and e.sourse.table_id == e.dest_id:
                continue
            subgraph = build_graph_in_depth(e.dest)
            merge_subgraph(G, subgraph, *[attr for attr in edge_template if getattr(e,attr,False) == True])
    return G

def build_full_graph(node):
    G1 = build_graph_up(node)
    G2 = build_graph_in_depth(node)
    G1.add_nodes_from(G2.nodes(data=True))
    G1.add_edges_from(G2.edges(data=True))
    return G1

# методы, списанные в утиль, могут пригодиться в дальнейшем
"""
def get_application_graph(app):
    G = nx.MultiDiGraph()
    G.add_node(app.id, label=app.label, node_class=app.__class__.__name__, id=app.id)
    for form in app.forms.values():
        subgraph = get_form_graph(form)
        G.add_nodes_from(subgraph.nodes(data=True))
        G.add_edges_from(subgraph.edges(data=True))
        G.add_edge(app.id, form.id, contain=True)
            
    return G

def get_form_graph(form):
    G = nx.MultiDiGraph()
    G.add_node(form.id, label=form.label, node_class=form.__class__.__name__)
    for component in form.components.values():
        subgraph = get_query_graph(component)
        G.add_nodes_from(subgraph.nodes(data=True))
        G.add_edges_from(subgraph.edges(data=True))
        G.add_edge(form.id, component.id, contain=True)
    return G

def get_query_graph(query):
    G = nx.MultiDiGraph()
    edge_template = ["select", "insert", "update", "delete", "exec", "drop", "truncate"]
    G.add_node(query.id, label=query.label, node_class=query.__class__.__name__, id=query.id)
    for e in query.edges_out:
        # защита от рекурсивных вызовов, где ребро графа циклическое
        if e.sourse.id == e.dest.id:
            continue
        subgraph = get_query_graph(e.dest)
        G.add_nodes_from(subgraph.nodes(data=True))
        G.add_edges_from(subgraph.edges(data=True))
        for attr in edge_template:
            if getattr(e, attr, False) == True:
                G.add_edge(query.id, e.dest.id, **{attr: True})
    return G

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
            graph.add_node(e.dest.id, label=e.dest.label, id=e.dest.id)
            graph.add_edge(obj.id, e.dest.id, **{attr: getattr(e, attr) for attr in edge_template})
    if len(next_wave) > 0 and iteration <= 30:
        dig_for_dependencies(graph, next_wave, iteration+1)
"""
