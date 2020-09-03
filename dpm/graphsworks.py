import networkx as nx


"""
Этот модуль запрашивает информацию о зависимостях объектов из базы и формирует
на основе полученных данных графы зависимостей объектов.
Полученные таким образом графы могут быть использованы для вывода данных в GUI
или для анализа данных;

При формировании графа все вершины и рёбра должны быть
размечены определённым образом:

Атрибуты вершин:
    node_class - содержит класс ORM-модели;
    node_id - id ноды из базы;

Атрибуты рёбер:
    select, insert, update, delete, exec, drop, truncate, contain, trigger,
    calc - ставится True/False, показывает набор операций, которые
    объект A осуществляет с объектом B.

Атрибуты нужны для того, чтобы при обработке графа можно было отличить,
например, ноду таблицы от ноды формы, правильно визуализировать связи
нужных типов, дозапрашивать данные из базы по id объекта.
"""

# ToDo настройки визуализации в config.json


class DpmGraph:
    """
    Класс, отвечающий за обработку графовых данных, при этом умеющий также
    подгружать информацию из БД.
    """

    def __init__(self, storage, pov_node, nx_graph=None):
        self._storage = storage
        self.pov_id = pov_node.id
        if nx_graph is None:
            # nx_graph - основной граф, отражающий реальную структуру зависимостей
            self.nx_graph = nx.MultiDiGraph()
            self._add_nx_node_from_model(pov_node)
        else:
            self.nx_graph = nx_graph
        self.levels_up = 0
        self.levels_down = 0
        self.reached_bottom_limit = False
        self.reached_upper_limit = False

    # region properties
    @property
    def nodes(self):
        return self.nx_graph.nodes()

    # endregion

    # region public methods
    def load_dependencies(self, levels_up=0, levels_down=0):
        zero_layer = [self._storage.get_node_by_id(self.pov_id)]
        if levels_down > 0:
            self._load_data_bfs(zero_layer, levels_down)
        if levels_up > 0:
            self._load_data_bfs(zero_layer, levels_up, reverse=True)

    def export_to_gexf(self):
        nx.write_gexf(self.nx_graph, f"{self[self.pov_id]['label']}.gexf", encoding="utf-8", prettyprint=True)
    # endregion

    # region utility methods
    def _load_data_bfs(self, previous_layer, depth, reverse=False):
        next_layer = []
        method_name = "get_parents" if reverse else "get_children"
        for node in previous_layer:
            for subnode, edge_attrs in getattr(node, method_name)():
                if subnode.id not in self.nx_graph:
                    self._add_nx_node_from_model(subnode)
                    next_layer.append(subnode)
                s, d = (subnode, node) if reverse else (node, subnode)
                self._add_edge(edge_attrs, source=s, destination=d)
        if depth > 1:
            self._load_data_bfs(next_layer, depth - 1, reverse=reverse)

    def _add_nx_node_from_model(self, model):
        """
        Добавляет в граф новую вершину, беря данные из её orm-модели.
        Поскольку набор атрибутов вершин может меняться, эта операция вынесена
        в отдельный метод.
        """
        self.nx_graph.add_node(
            model.id,
            label=model.label,
            node_class=model.__class__.__name__,
            id=model.id,
            peripheral=False,
            is_blind=False,
            is_revealed=False,
            in_cycle=False
        )

    def _add_edge(self, edge_attrs, source=None, destination=None):
        self.nx_graph.add_edge(source.id, destination.id, **edge_attrs)
    # endregion

    # region dunder methods
    def __getitem__(self, key):
        return self.nx_graph.node[key]

    def __iter__(self):
        return iter(self.nx_graph.node)
    # endregion
