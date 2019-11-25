import itertools
import networkx as nx
from .models import Node
import settings
from enum import IntEnum, auto
import re


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

# ToDo сделать послойную загрузку зависимостей вместо повершинной
# ToDo придумать, что делать со спрятанными вершинами при подгрузке зависимостей
# ToDo настройки визуализации в config.json

class GraphSearchResult:

    def __init__(self, search_word, graph, nodes=None):
        if nodes is not None:
            self.id_list_full = nodes
        else:
            self.id_list_full = []
        self.search_word = search_word
        self.graph = graph
        self.current_pos = 0
    
    # region Proprties
    @property
    def total(self):
        return len(self.id_list_full)
    
    
    @property
    def hidden_ids(self):
        return [id for id in self.id_list_full if self.graph[id]["status"] in (NodeStatus.ROLLED_UP, NodeStatus.AUTO_HIDDEN)]

    @property
    def has_hidden(self):
        return (len(self.hidden_ids) > 0)

    @property
    def visible_ids(self):
        return [id for id in self.id_list_full if self.graph[id]["status"] not in (NodeStatus.ROLLED_UP, NodeStatus.AUTO_HIDDEN)]

    @property
    def visible_nodes(self):
        return [self.graph[id] for id in self.visible_ids]

    @property
    def hidden_nodes(self):
        return [self.graph[id] for id in self.hidden_ids]
    # endregion
    
    # region public methods
    def add_node(self, node_id):
        self.id_list_full.append(node_id)
    
    def to_first(self):
        self.current_pos = 0
    
    def to_next(self):
        if len(self) == 0:
            return
        self.current_pos = (self.current_pos + 1) % len(self)

    def to_previous(self):
        if len(self) == 0:
            return
        self.current_pos = (self.current_pos - 1 + len(self)) % len(self)
    
    def get_current_match(self):
        if len(self) == 0:
            return None
        return self[self.current_pos]
    
    # endregion
    
    # region dunder methods
    def __str__(self):
        if len(self) == 0:
            if self.has_hidden:
                return f"Найдено {len(self.hidden_ids)} скрытых совпадений"
            else:
                return "Совпадений не найдено"
        elif self.has_hidden:
            return f"{self.current_pos + 1}-е из {len(self)} совпадений ({len(self.hidden_ids)} скрыто)"
        else:
            return f"{self.current_pos + 1}-е из {len(self)} совпадений"
    
    def __iter__(self):
        return iter(self.visible_nodes)
    
    def __getitem__(self, key):
        return self.visible_nodes[key]
    
    def __len__(self):
        return len(self.visible_ids)
    
    # endregion


class NodeStatus(IntEnum):
    NEW = 0
    VISIBLE = 1
    ROLLED_UP = 2
    AUTO_HIDDEN = 3


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
            # proxy_graph - заместитель для отображения
            self.proxy_graph = self.nx_graph.copy()
        else:
            self.nx_graph = nx_graph
            self.proxy_graph = self.nx_graph.copy()
        self.levels_up = 0
        self.levels_down = 0
        self.reached_bottom_limit = False
        self.reached_upper_limit = False
    
    # region properties
    @property
    def nodes(self):
        return self.nx_graph.nodes()
    
    @property
    def number_of_subordinate_nodes(self):
        """
        Возвращает количество вершин за вычетом POV.
        """
        return len(self.nx_graph.nodes())-1
    
    @property
    def auto_hidden_nodes(self):
        return [
            node 
            for node in self.nx_graph.node 
            if self.nx_graph.node[node]["status"] == NodeStatus.AUTO_HIDDEN
        ]
    # endregion

    # region public methods
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
            self.reached_upper_limit = self._load_dependencies_up(levels_up - self.levels_up)
        elif levels_up < self.levels_up:
            self._cut_upper_levels(levels_up)
            self.reached_upper_limit = False

        if levels_down > self.levels_down:
            self.reached_bottom_limit = self._load_dependencies_down(levels_down - self.levels_down)
        elif levels_down < self.levels_down:
            self._cut_lower_levels(levels_down)
            self.reached_bottom_limit = False
        self._recalc()
        self._rollup_inner_contour()
    
    def hide_node(self, node_id):
        self.nx_graph.node[node_id]["status"] = NodeStatus.ROLLED_UP
        self._prepare_graph_for_drawing()
    
    def show_node(self, node_id):
        self.nx_graph.node[node_id]["status"] = NodeStatus.VISIBLE
        self._prepare_graph_for_drawing()

    def show(self):
        """
        Рисует граф, применяя текущие настройки визуализации.
        """
        # красивая визуализация http://jonathansoma.com/lede/algorithms-2017/classes/networks/networkx-graphs-from-source-target-dataframe/
        config = settings.visualization
        pos = nx.spring_layout(self.proxy_graph, iterations=100)
        for class_name in config["nodes"]:
            nx.draw_networkx_nodes(
                self.proxy_graph, 
                pos, 
                [n for n in self.proxy_graph.node if self.proxy_graph.node[n]["node_class"]==class_name], 
                **config["nodes"][class_name]
            )
        for operation in config["edges"]:
            nx.draw_networkx_edges(
                self.proxy_graph, 
                pos, 
                [e for e in self.proxy_graph.edges if self.proxy_graph.adj[e[0]][e[1]][0].get(operation)==True], 
                **config["edges"][operation]
            )
        nx.draw_networkx_labels(
            self.proxy_graph, 
            pos, 
            {n:self.proxy_graph.node[n]["label"] for n in self.proxy_graph.node}, 
            font_size=6
        )

    def successors_of(self, node):
        return self.nx_graph.successors(node)

    def predecessors_of(self, node):
        return self.nx_graph.predecessors(node)
    
    def search_node(self, criterion):
        result_list = []
        for node_id in self.nx_graph.node:
            match = []
            for key in criterion:
                if key == "label":
                    label_match = False
                    if self.nx_graph.node[node_id]["label"] is not None:
                        result = re.search(criterion["label"], self.nx_graph.node[node_id]["label"])
                        if result is not None:
                            label_match = True
                    match.append(label_match)
                else:
                    match.append(self.nx_graph.node[node_id][key] == criterion[key])
            if all(match):
                result_list.append(node_id)
        print([self.nx_graph.node[node_id]["label"] for node_id in result_list])
        return result_list

    # endregion

    # region utility methods
    def _cut_upper_levels(self, limit):
        """
        Удаляет вершины, длина кратчайшего пути от которых к POV превышает limit.
        """
        length = dict(nx.single_target_shortest_path_length(self.nx_graph, self.pov_id))
        for node_id in length:
            if length[node_id] > limit:
                self.nx_graph.remove_node(node_id)

    def _cut_lower_levels(self, limit):
        """
        Удаляет вершины, длина кратчайшего пути от POV к которым превышает limit.
        """
        length = nx.single_source_shortest_path_length(self.nx_graph, self.pov_id)
        for node_id in length:
            if length[node_id] > limit:
                self.nx_graph.remove_node(node_id)

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
        rising_failed = []
        for node in self._storage.get_group_of_nodes_by_ids(upper_periphery):
            rising_failed.append(self._explore_upper_nodes(node, levels_counter))
        return all(rising_failed)

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
        digging_failed = []
        for node in self._storage.get_group_of_nodes_by_ids(bottom_periphery):
            digging_failed.append(self._explore_lower_nodes(node, levels_counter))
        return all(digging_failed)

    def _explore_lower_nodes(self, node, levels_counter):
        """
        Закапывается на levels_counter уровней вглубь зависимостей указанной вершины.
        Возвращает True, если закопаться на нужное количество уровней не удалось и поиск
        окончился раньше времени.
        Это значение служит индикатором того, что граф исследован вглубь до конца.
        """
        children = node.get_children()
        if len(children) == 0:
            # если у вершины нет потомков, то помечаем её как периферийную
            self._set_node_as_peripheral(node.id)
            return True
        digging_failed = []
        for child, edge_attrs in children:
            # если новая вершина ещё не добавлена в граф, то добавляем её id в граф и прописываем все атрибуты
            if child.id not in self.nx_graph:
                self._add_nx_node_from_model(child)
                # исследуем дочернюю вершину, если нужно углубиться
                # ещё на несколько уровней
                # и сохраняем результат
                if levels_counter > 1:
                    digging_failed.append(self._explore_lower_nodes(child, levels_counter-1))
            else:
                # если вершина уже в графе, то проверяем является ли она периферийной
                digging_failed.append(self._check_node_is_peripheral(child.id))
            # присоединяем дочернюю вершину к родительской, создавая ребро графа для каждой операции
            for attr in edge_attrs:
                self._add_edge(node, child, attr)
        return all(digging_failed)

    def _explore_upper_nodes(self, node, levels_counter):
        """
        Закапывается на levels_counter уровней вверх по зависимостям указанной вершины.
        Возвращает True, если подняться на нужное количество уровней не удалось и поиск
        окончился раньше времени. 
        Это значение служит индикатором того, что граф исследован вверх до конца.
        """
        parents = node.get_parents()
        if len(parents) == 0:
            # если у вершины нет предков, то помечаем её как периферийную
            self._set_node_as_peripheral(node.id)
            return True
        rising_failed = []
        for parent, edge_attrs in node.get_parents():
            # если новая вершина ещё не добавлена в граф, то добавляем её id в граф и прописываем все атрибуты
            if parent.id not in self.nx_graph:
                self._add_nx_node_from_model(parent)
                # исследуем дочернюю вершину, если нужно 
                # подняться ещё на несколько уровней
                # и сохраняем результат
                if levels_counter > 1:
                    rising_failed.append(self._explore_upper_nodes(parent, levels_counter-1))
            else:
                # если вершина уже в графе, то проверяем является ли она периферийной
                rising_failed.append(self._check_node_is_peripheral(parent.id))
            # присоединяем родительскую вершину к дочерней, создавая ребро графа для каждой операции
            for attr in edge_attrs:
                self._add_edge(parent, node, attr)
        return all(rising_failed)
    
    def _set_node_as_peripheral(self, node_id):
        self.nx_graph.node[node_id]["peripheral"] = True
    
    def _check_node_is_peripheral(self, node_id):
        return self.nx_graph.node[node_id]["peripheral"]

    def _add_nx_node_from_model(self, model):
        """
        Добавляет в граф новую вершину, беря данные из её orm-модели.
        Поскольку набор атрибутов вершин может меняться, эта операция вынесена в отдельный метод.
        """
        self.nx_graph.add_node(
            model.id,
            label=model.label,
            node_class=model.__class__.__name__,
            id=model.id,
            status=NodeStatus.NEW,
            peripheral=False
        )
        
    
    def _add_edge(self, source, dest, attr):
        self.nx_graph.add_edge(source.id, dest.id, **{attr: True})

    def _recalc(self):
        """
        Обходит граф, считая максимальные длины путей в центральную вершину и из неё.
        """
        path_down = nx.single_source_shortest_path_length(self.nx_graph, self.pov_id)
        path_up = dict(nx.single_target_shortest_path_length(self.nx_graph, self.pov_id))

        self.levels_down = max([length for length in path_down.values()])
        self.levels_up = max([length for length in path_up.values()])
    
    def _rollup_inner_contour(self):
        """
        Помечает все вновь загруженные вершины, непосредственно примыкающие к точке отсчёта, 
        как свёрнутые и убирает их из подставного графа (они перестают отображаться при визуализации).
        """
        for node in itertools.chain(self.nx_graph.predecessors(self.pov_id), self.nx_graph.successors(self.pov_id)):
            if self.nx_graph.node[node]["status"] == NodeStatus.NEW:
                self.nx_graph.node[node]["status"] = NodeStatus.ROLLED_UP
        self._prepare_graph_for_drawing()
    
    def _prepare_graph_for_drawing(self):
        """
        Вычищает из подставного графа все скрытые вершины и все вершины,
        которые после этого повисают без связи с точкой отсчёта.
        """
        self.proxy_graph = self.nx_graph.copy()
        rolled_up_nodes = [node for node in self.proxy_graph.node if self.proxy_graph.node[node]["status"] == NodeStatus.ROLLED_UP]
        for node in rolled_up_nodes:
            self.proxy_graph.remove_node(node)
        # находим компоненты связности и удаляем их все, кроме той в которой находится точка отсчёта
        for comp in list(nx.weakly_connected_components(self.proxy_graph)):
            if not self.pov_id in comp:
                for node in comp:
                    self.proxy_graph.remove_node(node)
        # Сопоставляем основной и замещающий граф, помечает несвёрнутые ноды первого, отсутствующие
        # во втором как скрытые.
        for node in self.nx_graph.node:
            if not node in self.proxy_graph.node and self.nx_graph.node[node]["status"] != NodeStatus.ROLLED_UP:
                self.nx_graph.node[node]["status"] = NodeStatus.AUTO_HIDDEN
            elif node in self.proxy_graph.node:
                self.nx_graph.node[node]["status"] = NodeStatus.VISIBLE

    # endregion
    
    # region dunder methods
    def __getitem__(self, key):
        return self.nx_graph.node[key]
    # endregion
