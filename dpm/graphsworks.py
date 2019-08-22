import networkx as nx
import dpm.models as models
import itertools
from node_storage import NodeStorage

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


class DpmGraph:

    # TBD как быть, если требуется загрузить зависимости вниз на 6 уровней,
    # а существует всего 5, тогда в атрибутах графа проставится 6, а по факту глубина
    # будет меньше

    def __init__(self, storage, nx_graph, pov_node):
        self.storage = storage
        self.nx_graph = nx_graph
        self.pov_id = pov_node.id
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
        for node_id in length:
            if length[node_id] > limit:
                self.nx_graph.remove(node_id)

    def _cut_lower_levels(self, limit):
        """
        Удаляет вершины, длина кратчайшего пути от POV к которым превышает limit.
        """
        length = nx.single_source_shortest_path_length(self.nx_graph, self.pov_id)
        for node_id in length:
            if length[node_id] > limit:
                self.nx_graph.remove(node_id)

    def _load_dependencies_up(self, levels_counter):
        """
        Подгружает связи в графе на levels_counter уровней вверх.
        """
        # ищем крайние вершины графа
        upper_periphery = set()
        length = dict(nx.single_target_shortest_path_length(self.nx_graph, self.pov_id))
        for node_id in length:
            if length[node_id] == self.levels_up:
                upper_periphery.add(node_id)
        # используем набор крайних вершин как отправную точку для поиска
        while upper_periphery:
            next_node = self.storage.get_node_by_id(upper_periphery.pop())
            self._explore_upper_nodes(next_node, levels_counter)

    def _load_dependencies_down(self, levels_counter):
        """
        Подгружает связи в графе на levels_counter уровней вниз.
        """
        # ищем вершины графа, максимально удалённые от pov на данный момент
        bottom_periphery = set()
        length = nx.single_source_shortest_path_length(self.nx_graph, self.pov_id)
        for node_id in length:
            if length[node_id] == self.levels_down:
                bottom_periphery.add(node_id)
        # используем набор крайних вершин как отправную точку для поиска
        while bottom_periphery:
            next_node = self.storage.get_node_by_id(bottom_periphery.pop())
            # ToDo можно привести id к объекту где-то здесь
            self._explore_lower_nodes(next_node, levels_counter)

    def _explore_lower_nodes(self, node, levels_counter):
        """
        Закапывается на levels_counter уровней вглубь зависимостей указанной вершины.
        """
        for child, edge_attrs in node.get_children():
            # если новая вершина ещё не добавлена в граф, то добавляем её id в граф и прописываем все атрибуты
            if child.id not in self.nx_graph:
                self._add_nx_node_from_model(child)
                # если нужно углубиться ещё на несколько уровней
                if levels_counter > 1:
                    self._explore_lower_nodes(child, levels_counter-1)
            # присоединяем дочернюю вершину к родительской, создавая ребро графа для каждой операции
            for attr in edge_attrs:
                self.nx_graph.add_edge(node.id, child.id, **{attr: True})

    def _explore_upper_nodes(self, node, levels_counter):
        """
        Закапывается на levels_counter уровней вверх по зависимостям указанной вершины.
        """
        for parent, edge_attrs in node.get_parents():
            # если новая вершина ещё не добавлена в граф, то добавляем её id в граф и прописываем все атрибуты
            if parent.id not in self.nx_graph:
                self._add_nx_node_from_model(parent)
                # если нужно углубиться ещё на несколько уровней
                if levels_counter > 1:
                    self._explore_upper_nodes(parent, levels_counter-1)
            # присоединяем родительскую вершину к дочерней, создавая ребро графа для каждой операции
            for attr in edge_attrs:
                self.nx_graph.add_edge(parent.id, node.id, **{attr: True})
    
    def _add_nx_node_from_model(self, model):
        """
        Добавляет в граф новую вершину, беря данные из её orm-модели.
        Поскольку набор атрибутов вершин может меняться, эта операция вынесена в отдельный метод.
        """
        self.nx_graph.add_node(model.id, label=model.label, node_class=model.__class__.__name__, id=model.id)

    def _recalc(self):
        pass

    def show(self):
        """
        Рисует граф, применяя текущие настройки визуализации.
        """
        pass
