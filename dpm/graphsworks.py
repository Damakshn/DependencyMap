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
    # используем по отдельности поля scalar_functions, procedures и др. вместо scripts
    # так как оно включает в себя триггеры, а их мы подберём, строя графы для таблиц
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
    # закапывается в зависимости очередной вершины и соединяет её рёбрами
    # с родительской вершиной в графе

    # защита от бесконечной рекурсии
    # закапываемся в зависимости вершины только тогда, когда её ещё нет в графе
    if not dest.id in G:
        fill_graph_in_depth(G, dest)
    # создаём по ребру от sourse к dest для каждой операции в edge_attrs
    for attr in edge_attrs:
        G.add_edge(sourse.id, dest.id, **{attr: True})

def connect_upper_node(G, dest, sourse, *edge_attrs):
    # выкапывается от очередной вершины вверх по иерархии и соединяет её рёбрами
    # с вершиной-потомком в графе

    # защита от бесконечной рекурсии
    # закапываемся в зависимости вершины только тогда, когда её ещё нет в графе
    if not sourse.id in G:
        fill_graph_up(G, sourse)

    for attr in edge_attrs:
        G.add_edge(sourse.id, dest.id, **{attr: True})


class DpmGraph:

    # TBD как быть, если требуется загрузить зависимости вниз на 6 уровней,
    # а существует всего 5, тогда в атрибутах графа проставится 6, а по факту глубина
    # будет меньше

    def __init__(self, nx_graph, pov_id):
        self.nx_graph = nx_graph
        self.pov_id = pov_id
        self.levels_up = 0
        self.levels_down = 0

    def hide_element(self, node_id):
        """
        Помечает вершину с id=node_id как hidden=True, а также все вершины, которые достижимы
        из POV только через эту вершину.
        """
        pass

    def load_dependencies(self, levels_up=0, levels_down=0):
        """
        Приводит граф к состоянию, когда у POV-вершины глубина восходящих связей 
        не более чем levels_up и глубина нисходящих связей не более чем levels_down.

        В качестве обоих параметров может быть передано float("inf"), в этом случае
        связи следует загружать до конца, то есть пока не закончатся объекты, имеющие связи.

        Если глубина связей в любом направлении превосходит текущее значение, то новые связи должны быть
        загружены из БД;
        если наоборот, текущая глубина связей больше требуемой, то все лишние вершины и рёбра будут удалены.
        """
        if (levels_up == self.levels_up) and (levels_down == self.levels_down):
            return

        if levels_up > self.levels_up:
            self._load_dependencies_up(levels_up - self.levels_up)
        elif levels_up < self.levels_up:
            self._cut_upper_levels(levels_up)

        if levels_down > self.levels_down:
            self._load_dependencies_down(levels_down - self.levels_down)
        elif levels_down < self.levels_down:
            self._cut_lower_levels(levels_down)

        self.levels_up = levels_up
        self.levels_down = levels_down

        self._recalc()

    def _cut_upper_levels(self, limit):
        """
        Удаляет вершины, длина кратчайшего пути от которых к POV превышает limit.
        """
        length = dict(nx.single_target_shortest_path_length(self.nx_graph, self.pov_id))
        for node in length:
            if length[node] > limit:
                self.nx_graph.remove(node)

    def _cut_lower_levels(self, limit):
        """
        Удаляет вершины, длина кратчайшего пути от POV к которым превышает limit.
        """
        length = nx.single_source_shortest_path_length(self.nx_graph, self.pov_id)
        for node in length:
            if length[node] > limit:
                self.nx_graph.remove(node)

    def _load_dependencies_up(self, levels_counter):
        """
        Подгружает связи в графе на levels_counter уровней вверх.
        """
        # ищем вершины графа, максимально удалённые от pov на данный момент
        upper_periphery = set()
        length = dict(nx.single_target_shortest_path_length(self.nx_graph, self.pov_id))
        for node in length:
            if length[node] == self.levels_up:
                upper_periphery.add(node)
        # используем набор крайних вершин как отправную точку для поиска
        while upper_periphery:
            next_node = upper_periphery.pop()
            self._explore_upper_nodes(next_node, levels_counter)

    def _load_dependencies_down(self, levels_counter):
        """
        Подгружает связи в графе на levels_counter уровней вниз.
        """
        # ищем вершины графа, максимально удалённые от pov на данный момент
        bottom_periphery = set()
        length = nx.single_source_shortest_path_length(self.nx_graph, self.pov_id)
        for node in length:
            if length[node] == self.levels_down:
                bottom_periphery.add(node)
        # используем набор крайних вершин как отправную точку для поиска
        while bottom_periphery:
            next_node = bottom_periphery.pop()
            self._explore_lower_nodes(next_node, levels_counter)

    def _explore_lower_nodes(self, node, levels_counter):
        """
        Закапывается на levels_counter уровней вглубь зависимостей указанной вершины.
        """
        # ToDo в отличие от старой версии, node - это id вершины, а не orm-моделька
        # как будем определять тип? передаём в объект сессию? приделываем к каждой ноде модельку?

        # [добываем выше/нижележащие вершины, действуя в зависимости от типа текущей вершины] см. fill_graph_in_depth
        # если новая вершина ещё не добавлена в граф, то добавляем её id в граф и прописываем все атрибуты
		# присоединяем эти вершины к данной, опираясь на тип связи
		# если levels_counter > 1:
		# для каждой вершины выполняем данный метод, уменьшив levels_counter на 1
        pass
    
    def _explore_upper_nodes(self, node, levels_counter):
        """
        Поднимается на levels_counter уровней вверх по зависимостям указанной вершины.
        """
        # [добываем выше/нижележащие вершины, действуя в зависимости от типа текущей вершины] см. fill_graph_up
        # если новая вершина ещё не добавлена в граф, то добавляем её id в граф и прописываем все атрибуты
		# присоединяем эти вершины к данной, опираясь на тип связи, 
		# если levels_counter > 1:
		# для каждой вершины выполняем данный метод, уменьшив levels_counter на 1
        pass

    def _recalc(self):
        pass

    def show(self):
        """
        Рисует граф, применяя текущие настройки визуализации.
        """
        pass
