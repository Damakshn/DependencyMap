from dpm.graphsworks import DpmGraph, NodeStatus
from PySide2 import QtWidgets, QtGui, QtCore
from .collection import IconCollection
from enum import Enum, auto


class TreeDirection(Enum):
    UP = auto()
    DOWN = auto()
    BOTH = auto()

class HistoryPoint:
    """
    Класс-обёртка для графа зависимостей и моделей данных PyQt,
    представляющих его в виде таблицы и дерева.
    """

    STATUS_COLUMN_INDEX = 3
    
    def __init__(self, session, initial_node, grouping=False):
        self.graph = DpmGraph(session, initial_node)
        self.pov_id = initial_node.id
        self.table_model = None
        self.tree_model = None
        self._refresh_table_model()
        self._refresh_tree_model()
        self.grouping = grouping
    
    # region properties
    @property
    def table_columns(self):
        return [
            {"header": "Тип объекта", "width": 35, "hidden": False},
            {"header": "ID", "width": 100, "hidden": True},
            {"header": "Имя", "width": 400, "hidden": False},
            {"header": "Статус", "width": 100, "hidden": True},
        ]
    
    @property
    def active_model(self):
        if self.grouping:
            return self.tree_model
        else:
            return self.table_model
    
    @property
    def number_of_nodes_in_list(self):
        """
        Количество вершин, отображаемых в списке.
        """
        return self.graph.number_of_subordinate_nodes - len(self.graph.auto_hidden_nodes)
    
    @property
    def number_of_auto_hidden_nodes(self):
        """
        Количество вершин, скрытых автоматически при скрытии вершины пользователем.
        """
        return len(self.graph.auto_hidden_nodes)
    
    @property
    def total_number_of_nodes(self):
        """
        Сколько всего вершин в графе
        """
        return len(self.graph.nodes)
    
    @property
    def number_of_subordinate_nodes(self):
        """
        Количество подчинённых вершин (за вычетом точки отсчёта)
        """
        self.graph.number_of_subordinate_nodes
    
    @property
    def levels_down(self):
        return self.graph.levels_down
    
    @property
    def levels_up(self):
        return self.graph.levels_up
    
    @property
    def reached_bottom_limit(self):
        return self.graph.reached_bottom_limit
    
    @property
    def reached_upper_limit(self):
        return self.graph.reached_upper_limit
    
    @property
    def pov_node_class(self):
        return self.graph[self.pov_id]["node_class"]
    
    @property
    def pov_node_label(self):
        return self.graph[self.pov_id]["label"]
    
    # endregion
    
    # region public methods
    def load_dependencies(self, up, down):
        self.graph.load_dependencies(levels_up=up, levels_down=down)
        self._refresh_table_model()
        self._refresh_tree_model()
    
    def set_grouping_enagled(self, enabled):
        self.grouping = enabled

    def show_graph(self):
        self.graph.show()
    
    def hide_node(self, model_index):
        row_num = model_index.row()
        node_id = int(self.active_model.data(self.active_model.index(row_num, 1)))
        # модифицируем модель данных, чтобы указать, что нода спрятана пользователем
        self.active_model.setData(self.active_model.index(row_num, self.STATUS_COLUMN_INDEX), str(int(NodeStatus.ROLLED_UP)))
        # красим строку
        self._paint_row_as_rolled_up(row_num)
        # прячем ноду в самом графе
        self.graph.hide_node(node_id)
        
        # помечаем в модели те объекты, которые были скрыты автоматически
        nodes_to_hide = self.graph.auto_hidden_nodes
        for row in range(self.active_model.rowCount()):
            if int(self.active_model.index(row, 1).data()) in nodes_to_hide:
                self.active_model.setData(self.active_model.index(row, self.STATUS_COLUMN_INDEX), str(int(NodeStatus.AUTO_HIDDEN)))
    
    def show_node(self, model_index):
        row_num = model_index.row()
        node_id = int(self.active_model.data(self.active_model.index(row_num, 1)))
        # модифицируем модель данных, чтобы указать, что нода снова видима
        self.active_model.setData(self.active_model.index(row_num, self.STATUS_COLUMN_INDEX), str(int(NodeStatus.VISIBLE)))
        # красим строку обратно
        self._paint_row_as_visible(row_num)
        # обрабатываем граф
        self.graph.show_node(node_id)
        # снимаем метку с тех вершин, которые должны стать видимыми
        nodes_to_hide = self.graph.auto_hidden_nodes
        for row in range(self.active_model.rowCount()):
            if int(self.active_model.index(row, 1).data()) not in nodes_to_hide and int(str(self.active_model.index(row, 3).data())) != NodeStatus.ROLLED_UP:
                self.active_model.setData(self.active_model.index(row, self.STATUS_COLUMN_INDEX), str(int(NodeStatus.VISIBLE)))
    
    def _create_model_row_from_node(self, node_id):
        icon = QtGui.QStandardItem(IconCollection.get_icon_for_node_class(self.graph[node_id]["node_class"]), "")
        id = QtGui.QStandardItem(str(self.graph[node_id]["id"]))
        name = QtGui.QStandardItem(self.graph[node_id]["label"])
        status = QtGui.QStandardItem(str(int(self.graph[node_id]["status"])))
        return [icon, id, name, status]
    
    # endregion
    
    # region utility methods
    def _refresh_table_model(self):
        """
        Полностью обновляет табличную модель на основе графа.
        """
        if self.table_model is None:
            self.table_model = QtGui.QStandardItemModel()
        else:
            self.table_model.clear()
        self.table_model.setHorizontalHeaderLabels([c["header"] for c in self.table_columns])
        for node_id in self.graph.nodes:
            if node_id == self.graph.pov_id:
                continue
            new_row = self._create_model_row_from_node(node_id)
            self.table_model.appendRow(new_row)
        for row in range(self.table_model.rowCount()):
            if int(self.table_model.data(self.table_model.index(row, self.STATUS_COLUMN_INDEX))) == NodeStatus.ROLLED_UP:
                self._paint_row_as_rolled_up(row)
    
    def _create_tree_row_from_node(self, node_id, direction):
        new_row = self._create_model_row_from_node(node_id)
        row_anchor = new_row[0]
        folder_items = []

        if (direction is TreeDirection.DOWN or direction is TreeDirection.BOTH) and len(list(self.graph.successors_of(node_id))) > 0:
            folder_items.append({
                "item": QtGui.QStandardItem(IconCollection.icons["tree_down"], ""),
                "node_list": self.graph.successors_of(node_id),
                "direction": TreeDirection.DOWN
            })
        elif (direction is TreeDirection.UP or direction is TreeDirection.BOTH) and len(list(self.graph.predecessors_of(node_id))) > 0:
            folder_items.append({
                "item": QtGui.QStandardItem(IconCollection.icons["tree_up"], ""),
                "node_list": self.graph.predecessors_of(node_id),
                "direction": TreeDirection.UP
            })
        else:
            return new_row
        
        for fitem in folder_items:
            item_anchor = fitem["item"]
            row_anchor.appendRow(item_anchor)
            for node_id in fitem["node_list"]:
                item_anchor.appendRow(self._create_tree_row_from_node(node_id, fitem["direction"]))
        return new_row
        
    
    def _refresh_tree_model(self):
        """
        Конвертирует граф в древовидную модель для виджета.
        """
        if self.tree_model is None:
            self.tree_model = QtGui.QStandardItemModel()
        else:
            self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels([c["header"] for c in self.table_columns])
        root_item = self.tree_model.invisibleRootItem()
        root_item.appendRow(self._create_tree_row_from_node(self.pov_id, TreeDirection.BOTH))
    
    def _paint_row_as_rolled_up(self, row):
        for column in range(len(self.table_columns)):
            self.active_model.setData(
                self.active_model.index(row, column), 
                QtGui.QBrush(QtCore.Qt.lightGray),
                QtCore.Qt.BackgroundRole
            )
    
    def _paint_row_as_visible(self, row):
        for column in range(len(self.table_columns)):
            self.active_model.setData(
                self.active_model.index(row, column), 
                QtGui.QBrush(QtCore.Qt.white), 
                QtCore.Qt.BackgroundRole
            )
    # endregion
