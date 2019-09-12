import networkx as nx
from .models import Node
import settings

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

class DpmGraph:

    """
    Класс, отвечающий за обработку графовых данных, при этом умеющий также
    подгружать информацию из БД.
    """
   
    def __init__(self, session, pov_node, nx_graph=None):
        self.session = session
        self.pov_id = pov_node.id
        if nx_graph is None:
            # nx_graph - основной граф, отражающий реальную структуру зависимостей
            self.nx_graph = nx.MultiDiGraph()
            # proxy_graph - заместитель для отображения
            self.proxy_graph = nx.MultiDiGraph()
            self._add_nx_node_from_model(pov_node)
        else:
            self.nx_graph = nx_graph
            self.proxy_graph = self.nx_graph.copy()
        self.levels_up = 0
        self.levels_down = 0
        self.reached_bottom_limit = False
        self.reached_upper_limit = False

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
        rising_failed = []
        for node in self.session.query(Node).filter(Node.id.in_(upper_periphery)).all():
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
        for node in self.session.query(Node).filter(Node.id.in_(bottom_periphery)).all():
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
            hidden=False,
            hidden_by_user=False,
            peripheral=False
        )
        self.proxy_graph.add_node(
            model.id,
            label=model.label,
            node_class=model.__class__.__name__,
            id=model.id,
            hidden=False
        )
    
    def _add_edge(self, source, dest, attr):
        self.nx_graph.add_edge(source.id, dest.id, **{attr: True})
        self.proxy_graph.add_edge(source.id, dest.id, **{attr: True})

    def _recalc(self):
        """
        Обходит граф, считая максимальные длины путей в центральную вершину и из неё.
        """
        path_down = nx.single_source_shortest_path_length(self.nx_graph, self.pov_id)
        path_up = dict(nx.single_target_shortest_path_length(self.nx_graph, self.pov_id))

        self.levels_down = max([length for length in path_down.values()])
        self.levels_up = max([length for length in path_up.values()])
    
    def _mark_hidden_nodes_after_purging(self):
        """
        Сопоставляет основной и замещающий граф, помечает ноды первого, отсутствующие
        во втором как скрытые. Атрибут hidden_by_user не ставится, чтобы указать,
        что эти ноды скрыты автоматически.
        """
        for node in self.nx_graph.node:
            if not node in self.proxy_graph.node:
                self.nx_graph.node[node]["hidden"] = True
    
    def _purge_proxy_graph(self):
        """
        Вычищает из подставного графа все скрытые вершины и все вершины,
        которые после этого повисают без связи с точкой отсчёта.
        """
        hidden_nodes = [node for node in self.proxy_graph.node if self.proxy_graph.node[node]["hidden"]]
        for node in hidden_nodes:
            self.proxy_graph.remove_node(node)
        for comp in list(nx.weakly_connected_components(self.proxy_graph)):
            if not self.pov_id in comp:
                for node in comp:
                    self.proxy_graph.remove_node(node)
        self._mark_hidden_nodes_after_purging()
    
    
    def hide_node(self, node_id):
        self.nx_graph.node[node_id]["hidden"] = True
        self.nx_graph.node[node_id]["hidden_by_user"] = True
        self.proxy_graph.node[node_id]["hidden"] = True
        self._purge_proxy_graph()

    
    def show_node(self, node_id):
        self.nx_graph.node[node_id]["hidden"] = False
        self.nx_graph.node[node_id]["hidden_by_user"] = False
        self.proxy_graph = self.nx_graph.copy()
        self._purge_proxy_graph()

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
        return [node for node in self.nx_graph.node if self.nx_graph.node[node]["hidden"] and not self.nx_graph.node[node]["hidden_by_user"]]

    def __getitem__(self, key):
        return self.nx_graph.node[key]
