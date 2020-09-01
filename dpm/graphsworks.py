from enum import IntEnum
import itertools
import re
import networkx as nx
from networkx.algorithms.cycles import simple_cycles
import settings


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

# ToDo сделать послойную загрузку зависимостей вместо повершинной
# ToDo придумать, что делать со спрятанными вершинами при подгрузке зависимостей
# ToDo настройки визуализации в config.json


class NodeStatus(IntEnum):
    """
    Перечисление, содержащее возможные статусы вершин графа.
    Статусы влияют на видимость вершин в виджетах GUI и видимость при
    визуализации графа. В сочетании с другими свойствами, статусы
    также определяют набор действий, которые можно выполнять с
    вершинами через контекстное меню.

    VISIBLE
        вершина видна в списке и на графике, видны все её нескрытые потомки;
        допустимые действия:
            скрыть/свернуть в зависимости от наличия потомков.
        Этот статус имеют по умолчанию все вершины при загрузке из БД.
    ROLLED_UP
        вершина скрыта пользователем, видна в списке, но не видна на графике;
        потомки вершины не видны;
        доступные действия:
            Развернуть
    AUTO_HIDDEN
        вершина скрыта потому, что скрыт её предок;
        она не видна нигде; нет доступных действий;
    """
    VISIBLE = 0
    ROLLED_UP = 1
    AUTO_HIDDEN = 2


def changes_visiblity(method):
    """
    Декоратор, который нужно цеплять к каждому методу, изменяющему видимость
    вершин графа.
    Вычищает из прокси-графа все скрытые вершины и все вершины,
    которые после этого повисают без связи с точкой отсчёта.
    """
    def wrapper(*args, **kwargs):
        method(*args, **kwargs)
        graph = args[0]
        graph.proxy_graph = graph.nx_graph.copy()
        free_nodes = set(graph)

        def remove_invisible_neighbours(node_id):
            if node_id not in free_nodes:
                return
            free_nodes.remove(node_id)
            neighbours = [node for node in graph.neighbours_of(node_id) if node in free_nodes]
            visible = [node for node in neighbours if graph.is_visible_node(node)]
            # если рассматриваемая вершина свёрнута, сужаем критерий отбора видимых соседей
            if graph[node_id]["status"] == NodeStatus.ROLLED_UP:
                visible = [
                    node
                    for node in visible
                    if graph[node]["is_revealed"] or graph[node]["in_cycle"]
                ]
            invisible = [node for node in neighbours if node not in visible]
            for neighbour in invisible:
                free_nodes.remove(neighbour)
                graph.proxy_graph.remove_node(neighbour)
            for neighbour in visible:
                remove_invisible_neighbours(neighbour)

        remove_invisible_neighbours(graph.pov_id)

        """
        находим компоненты связности и удаляем их все, кроме той в которой
        находится точка отсчёта
        """
        for comp in list(nx.weakly_connected_components(graph.proxy_graph)):
            if graph.pov_id not in comp:
                for node in comp:
                    graph.proxy_graph.remove_node(node)
        """
        Сопоставляем основной и замещающий граф, помечает несвёрнутые ноды
        первого, отсутствующие во втором как скрытые.
        """
        for node in graph.nx_graph.node:
            if (node not in graph.proxy_graph.node and graph.nx_graph.node[node]["status"] != NodeStatus.ROLLED_UP):
                graph.nx_graph.node[node]["status"] = NodeStatus.AUTO_HIDDEN
            elif (node in graph.proxy_graph.node and graph.nx_graph.node[node]["status"] != NodeStatus.ROLLED_UP):
                graph.nx_graph.node[node]["status"] = NodeStatus.VISIBLE
    return wrapper


class DpmGraph:
    """
    Класс, отвечающий за обработку графовых данных, при этом умеющий также
    подгружать информацию из БД.

    Визуализация графов в networkx устроена так, что нельзя сказать методу отрисовки,
    что какие-то вершины в данный момент невидимы, он всегда рисует граф целиком.
    Чтобы обойти это ограничение, добавлен замещающий граф (proxy_graph), который
    выглядит в точности так, как должен отображаться исходный граф с учётом всех
    невидимых вершин.
    """

    def __init__(self, storage, pov_node, nx_graph=None):
        self._storage = storage
        self.pov_id = pov_node.id
        if nx_graph is None:
            # nx_graph - основной граф, отражающий реальную структуру зависимостей
            self.nx_graph = nx.MultiDiGraph()
            self._add_nx_node_from_model(pov_node)
            # proxy_graph - заместитель, используемый для визуализации
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
        Приводит граф к состоянию, когда у POV-вершины глубина восходящих
        связей не более чем levels_up и глубина нисходящих связей не
        более чем levels_down.

        В качестве обоих параметров может быть передано float("inf"),
        в этом случае связи следует загружать до конца, то есть пока не
        закончатся объекты, имеющие связи.

        Если глубина связей в любом направлении превосходит текущее
        значение, то новые связи должны быть загружены из БД;
        если наоборот, текущая глубина связей больше требуемой,
        то все лишние вершины и рёбра будут удалены.
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

    @changes_visiblity
    def hide_node(self, node_id):
        self.nx_graph.node[node_id]["status"] = NodeStatus.ROLLED_UP

    @changes_visiblity
    def show_node(self, node_id):
        self.nx_graph.node[node_id]["status"] = NodeStatus.VISIBLE

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
                [n for n in self.proxy_graph.node if self.proxy_graph.node[n]["node_class"] == class_name],
                **config["nodes"][class_name]
            )
        for operation in config["edges"]:
            nx.draw_networkx_edges(
                self.proxy_graph,
                pos,
                [e for e in self.proxy_graph.edges if self.proxy_graph.adj[e[0]][e[1]][0].get(operation) is True],
                **config["edges"][operation]
            )
        nx.draw_networkx_labels(
            self.proxy_graph,
            pos,
            {n: self.proxy_graph.node[n]["label"] for n in self.proxy_graph.node},
            font_size=6
        )

    def successors_of(self, node_id):
        return self.nx_graph.successors(node_id)

    def predecessors_of(self, node_id):
        return self.nx_graph.predecessors(node_id)

    def neighbours_of(self, node_id):
        return list(
            itertools.chain(
                self.nx_graph.successors(node_id),
                self.nx_graph.predecessors(node_id))
        )

    def search_node(self, criterion):
        """
        Выполняет поиск среди вершин графа по заданным критериям.
        Критерии поиска передаются в виде словаря, ключи - атрибуты, которые
        нужно проверить, значения - то, что должно быть в этих атрибутах.

        Если нужно осуществлять поиск по названию вершины (атрибут label),
        то используется регулярное выражение.
        """
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
        return result_list

    def is_visible_node(self, node_id):
        """
        Возвращает True, если нода видима и в графе, и в списке.
        """
        in_cycle = self.nx_graph.node[node_id]["in_cycle"]
        is_revealed = self.nx_graph.node[node_id]["is_revealed"]
        is_pov = (node_id == self.pov_id)
        is_visible = (self.nx_graph.node[node_id]["status"] == NodeStatus.VISIBLE)
        return any([in_cycle, is_revealed, is_pov, is_visible])
        # return self.nx_graph.node[node_id]["status"] not in (NodeStatus.ROLLED_UP, NodeStatus.AUTO_HIDDEN)

    @changes_visiblity
    def reveal_hidden_nodes(self, node_list):
        """
        Показывает скрытые ноды из списка так, чтобы стали видны пути,
        соединяющие каждую ноду с точкой отсчёта. Ищет путь в обе стороны,
        ничего не предпринимает, если путь в одну из сторон не найден.
        В результате этой операции статусы вершин обновляются хитрым
        образом, см. комментарии ниже.
        """

        # содержит все ноды, лежащие на пути между точкой отсчёта
        # и теми нодами, что нужно показать
        nodes_in_path = set()
        for node_id in node_list:
            # получаем для каждой вершины путь из неё к точке отсчёта
            try:
                nodes_in_path.update(
                    nx.algorithms.shortest_paths.generic.shortest_path(
                        self.nx_graph,
                        source=node_id,
                        target=self.pov_id
                    )
                )
            except nx.exception.NetworkXNoPath:
                pass
            # и наоборот - из точки отсчёта к вершине
            try:
                nodes_in_path.update(
                    nx.algorithms.shortest_paths.generic.shortest_path(
                        self.nx_graph,
                        source=self.pov_id,
                        target=node_id
                    )
                )
            except nx.exception.NetworkXNoPath:
                pass
        # после перебора всех вершин исключаем из множества точку отсчёта,
        # потому что её статус не может изменяться
        nodes_in_path.remove(self.pov_id)
        # перебираем все вершины в пути, отмечаем их как открытые
        for node_id in nodes_in_path:
            # (self.nx_graph.node[node_id]["status"] != NodeStatus.VISIBLE) -> True
            self.nx_graph.node[node_id]["is_revealed"] = True

    # endregion

    # region utility methods
    def _cut_upper_levels(self, limit):
        """
        Удаляет вершины, длина кратчайшего пути от которых к POV
        превышает limit.
        """
        length = dict(nx.single_target_shortest_path_length(self.nx_graph, self.pov_id))
        for node_id in length:
            if length[node_id] > limit:
                self.nx_graph.remove_node(node_id)

    def _cut_lower_levels(self, limit):
        """
        Удаляет вершины, длина кратчайшего пути от POV к которым
        превышает limit.
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
        Закапывается на levels_counter уровней вглубь зависимостей
        указанной вершины.
        Возвращает True, если закопаться на нужное количество уровней
        не удалось и поиск окончился раньше времени.
        Это значение служит индикатором того, что граф исследован
        вглубь до конца.
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
                # если вершина уже в графе, то проверяем является ли
                # она периферийной
                digging_failed.append(self._check_node_is_peripheral(child.id))
            # присоединяем дочернюю вершину к родительской, создавая ребро
            # графа для каждой операции
            for attr in edge_attrs:
                self._add_edge(node, child, attr)
        return all(digging_failed)

    def _explore_upper_nodes(self, node, levels_counter):
        """
        Закапывается на levels_counter уровней вверх по зависимостям
        указанной вершины.
        Возвращает True, если подняться на нужное количество уровней не
        удалось и поиск окончился раньше времени.
        Это значение служит индикатором того, что граф исследован
        вверх до конца.
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
        Поскольку набор атрибутов вершин может меняться, эта операция вынесена
        в отдельный метод.
        """
        self.nx_graph.add_node(
            model.id,
            label=model.label,
            node_class=model.__class__.__name__,
            id=model.id,
            status=NodeStatus.VISIBLE,
            peripheral=False,
            is_blind=False,
            is_revealed=False,
            in_cycle=False
        )

    def _add_edge(self, source, dest, attr):
        self.nx_graph.add_edge(source.id, dest.id, **{attr: True})

    def _recalc(self):
        """
        Обходит граф, считая максимальные длины путей в центральную вершину и
        из неё.
        """
        path_down = nx.single_source_shortest_path_length(self.nx_graph, self.pov_id)
        path_up = dict(nx.single_target_shortest_path_length(self.nx_graph, self.pov_id))

        self.levels_down = max([length for length in path_down.values()])
        self.levels_up = max([length for length in path_up.values()])
        # поиск вершин без потомков
        for node in self.nx_graph.node:
            self.nx_graph.node[node]["is_blind"] = (not list(self.nx_graph.successors(node)))
        # поиск циклов, проходящих через точку отсчёта
        cycles = simple_cycles(self.nx_graph)
        cycles = list(filter(lambda cycle: self.pov_id in cycle, cycles))
        for node in set([node for cycle in cycles for node in cycle]):
            self[node]["in_cycle"] = True

    @changes_visiblity
    def _rollup_inner_contour(self):
        """
        Помечает все вновь загруженные вершины, непосредственно
        примыкающие к точке отсчёта, как свёрнутые и убирает их из
        подставного графа (они перестают отображаться при визуализации).

        Это нужно для того, чтобы при граф при визуализации имел
        более аккуратный вид.
        """
        for node in itertools.chain(self.nx_graph.predecessors(self.pov_id), self.nx_graph.successors(self.pov_id)):
            if self.is_visible_node(node):
                self.nx_graph.node[node]["status"] = NodeStatus.ROLLED_UP

    # endregion

    # region dunder methods
    def __getitem__(self, key):
        return self.nx_graph.node[key]

    def __iter__(self):
        return iter(self.nx_graph.node)
    # endregion
