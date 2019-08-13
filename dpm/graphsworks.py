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
    select, insert, update, delete, exec, drop, truncate, contain, trigger, calc - ставится True/False, показывает набор операций, которые
    объект A осуществляет с объектом B.

Атрибуты нужны для того, чтобы при обработке графа можно было отличить, например, ноду таблицы
от ноды формы, правильно визуализировать связи нужных типов, дозапрашивать данные из базы по id объекта.
"""


def build_graph_in_depth(node):
    """
    Строит граф объектов, от которых зависит заданный объект, рекурсивно копая вглубь.
    """
    G = nx.MultiDiGraph()
    fill_graph_in_depth(G, node)
    return G

def fill_graph_in_depth(G, parent_node):
    G.add_node(parent_node.id, label=parent_node.label, node_class=parent_node.__class__.__name__, id=parent_node.id)
    # не используем поле scripts, так как оно включает в себя триггеры, а их мы подберём, строя графы для таблиц
    if isinstance(parent_node, models.Database):
        for obj in itertools.chain(
            parent_node.tables.values(),
            parent_node.scalar_functions.values(),
            parent_node.table_functions.values(),
            parent_node.procedures.values(),
            parent_node.views.values()
        ):
            connect_deeper_node(G, parent_node, obj, "contain")
    elif isinstance(parent_node, models.Application):
        for form in parent_node.forms.values():
            connect_deeper_node(G, parent_node, form, "contain")
    elif isinstance(parent_node, models.Form):
        for component in parent_node.components.values():
           connect_deeper_node(G, parent_node, component, "contain")
    elif isinstance(parent_node, models.DBTable):
        for trigger in parent_node.triggers.values():
            connect_deeper_node(G, parent_node, trigger, "contain")
    else:
        edge_template = ["calc", "select", "insert", "update", "delete", "exec", "drop", "truncate"]
        for e in parent_node.edges_out:
            # защита от рекурсивных вызовов скалярных функций, где ребро графа циклическое
            if e.sourse.id == e.dest.id:
                continue
            # защита от зацикливания на триггерах
            if isinstance(e.sourse, models.DBTrigger) and e.sourse.table_id == e.dest_id:
                continue
            connect_deeper_node(G, parent_node, e.dest, *[attr for attr in edge_template if getattr(e,attr,False) == True])

def build_graph_up(node):
    """
    Строит граф объектов, зависимых от заданного, рекурсивно двигаясь вверх по иерархии объектов (изнутри наружу).
    """
    G = nx.MultiDiGraph()
    fill_graph_up(G, node)
    return G

def fill_graph_up(G, child_node):
    G.add_node(child_node.id, label=child_node.label, node_class=child_node.__class__.__name__, id=child_node.id)
    if isinstance(child_node, models.Database) or isinstance(child_node, models.Application):
        return
    elif isinstance(child_node, models.Form):
        for app in child_node.applications:
            G.add_node(app.id, label=app.label, node_class=app.__class__.__name__, id=app.id)
            G.add_edge(app.id, child_node.id, contain=True)
    elif isinstance(child_node, models.ClientQuery):
        connect_upper_node(G, child_node, child_node.form, "contain")
    else:
        edge_template = ["calc", "select", "insert", "update", "delete", "exec", "drop", "truncate"]
        for e in child_node.edges_in:
            # защита от рекурсивных вызовов, где ребро графа циклическое
            if e.sourse.id == e.dest.id:
                continue
            connect_upper_node(G, child_node, e.sourse, *[attr for attr in edge_template if getattr(e,attr,False) == True])

def build_full_graph(node):
    G1 = build_graph_up(node)
    G2 = build_graph_in_depth(node)
    G1.add_nodes_from(G2.nodes(data=True))
    G1.add_edges_from(G2.edges(data=True))
    return G1

def connect_deeper_node(G, sourse, dest, *edge_attrs):
    # защита от бесконечной рекурсии
    # закапываемся в зависимости вершины только тогда, когда её ещё нет в графе
    if not dest.id in G:
        fill_graph_in_depth(G, dest)

    for attr in edge_attrs:
        G.add_edge(sourse.id, dest.id, **{attr: True})

def connect_upper_node(G, dest, sourse, *edge_attrs):
    # защита от бесконечной рекурсии
    # закапываемся в зависимости вершины только тогда, когда её ещё нет в графе
    if not sourse.id in G:
        fill_graph_up(G, sourse)

    for attr in edge_attrs:
        G.add_edge(sourse.id, dest.id, **{attr: True})
