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
        self.graph.hide_node(node_id)
        self._update_node_statuses_in_models()
    
    def show_node(self, model_index):
        row_num = model_index.row()
        node_id = int(self.active_model.data(self.active_model.index(row_num, 1)))
        self.graph.show_node(node_id)
        self._update_node_statuses_in_models()
    
    # endregion
    
    # region utility methods
    def _refresh_table_model(self):
        """
        Полностью обновляет табличную модель на основе графа при подгрузке зависимостей.
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
                self._paint_row_as_rolled_up(self.table_model, row)

    def _refresh_tree_model(self):
        """
        Полностью обновляет древовидную модель на основе графа при подгрузке зависимостей.
        """
        if self.tree_model is None:
            self.tree_model = QtGui.QStandardItemModel()
        else:
            self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels([c["header"] for c in self.table_columns])
        root_item = self.tree_model.invisibleRootItem()
        root_item.appendRow(self._create_tree_row_from_node(self.pov_id, TreeDirection.BOTH))
        # древовидная модель сложнее табличной, после её заполнения данными из графа
        # нужно дополнительно пройти по вершинам и расставить им правильные статусы
        self._update_statuses_in_tree_model()
    
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
        node_status = self.graph[node_id]["status"]
        for fitem in folder_items:
            item_anchor = fitem["item"]
            # если нода спрятана, то стрелка тоже спрятана
            if node_status in (NodeStatus.ROLLED_UP, NodeStatus.AUTO_HIDDEN):
                anchor_status = str(int(NodeStatus.AUTO_HIDDEN))
            else:
                anchor_status = str(int(NodeStatus.VISIBLE))
            row_anchor.appendRow([item_anchor, QtGui.QStandardItem(), QtGui.QStandardItem(), QtGui.QStandardItem(anchor_status)])
            for node_id in fitem["node_list"]:
                item_anchor.appendRow(self._create_tree_row_from_node(node_id, fitem["direction"]))
        return new_row
    
    def _create_model_row_from_node(self, node_id):
        icon = QtGui.QStandardItem(IconCollection.get_icon_for_node_class(self.graph[node_id]["node_class"]), "")
        id = QtGui.QStandardItem(str(self.graph[node_id]["id"]))
        name = QtGui.QStandardItem(self.graph[node_id]["label"])
        status = QtGui.QStandardItem(str(int(self.graph[node_id]["status"])))
        return [icon, id, name, status]
    
    def _update_node_statuses_in_models(self):
        """
        Метод, обновляющий статусы вершин в моделях данных в те моменты,
        когда вершина прячется или показывается.
        """
        # табличная модель
        for row in range(self.table_model.rowCount()):
            id = int(self.table_model.index(row, 1).data())
            self.table_model.setData(self.table_model.index(row, self.STATUS_COLUMN_INDEX), str(int(self.graph[id]["status"])))
            if self.graph[id]["status"] == NodeStatus.VISIBLE:
                self._paint_row_as_visible(self.table_model, row)
            elif self.graph[id]["status"] == NodeStatus.ROLLED_UP:
                self._paint_row_as_rolled_up(self.table_model, row)
        # деревянная модель
        self._update_statuses_in_tree_model()
    
    def _update_statuses_in_tree_model(self):
        """
        Обновляет статусы объектов в древовидной модели.
        Дерево не является линейной структурой и один объект может
        встречаться в разных местах многократно, плюс у древовидного представления
        есть служебные строки (со стрелками), для группировки объектов по направлению связи (вниз и вверх).
        """
        root = self.tree_model.itemFromIndex(self.tree_model.index(0, 0)).index()
        stack = []
        stack.append(root)
        while len(stack) > 0:
            next_index = stack.pop()
            item = self.tree_model.itemFromIndex(next_index)
            row = item.row()
            parent = item.parent()
            parent_index = parent.index() if parent is not None else QtCore.QModelIndex()
            id = self.tree_model.index(row, 1, parent_index).data()
            id = int(id) if id is not None else None
            if parent is not None:
                parent_row = parent.row()
                praparent_index = parent.parent().index() if parent.parent() is not None else QtCore.QModelIndex()
                parent_status = int(self.tree_model.index(parent_row, self.STATUS_COLUMN_INDEX, praparent_index).data())
                new_status = int(NodeStatus.VISIBLE)
                # если родитель свёрнут или невидим, то помечаем строку как спрятанную
                if parent_status in (NodeStatus.AUTO_HIDDEN, NodeStatus.ROLLED_UP):
                    new_status = int(NodeStatus.AUTO_HIDDEN)
                # иначе (если это не стрелка) ставим фактический статус
                elif id is not None:
                    new_status = int(self.graph[id]["status"])
                # для стрелки просто копируем статус родителя
                else:
                    new_status = parent_status
                self.tree_model.setData(self.tree_model.index(row, self.STATUS_COLUMN_INDEX, parent_index), str(new_status))
                if new_status == NodeStatus.VISIBLE:
                    self._paint_row_as_visible(self.tree_model, row, parent=parent_index)
                elif new_status == NodeStatus.ROLLED_UP:
                    self._paint_row_as_rolled_up(self.tree_model, row, parent=parent_index)
            for row in range(item.rowCount()):
                child_index = self.tree_model.index(row, 0, next_index)
                stack.append(child_index)
    
    def _paint_row_as_rolled_up(self, model, row, parent=QtCore.QModelIndex()):
        item = model.itemFromIndex(model.index(row, 0, parent))
        item.setEnabled(False)

    def _paint_row_as_visible(self, model, row, parent=QtCore.QModelIndex()):
        item = model.itemFromIndex(model.index(row, 0, parent))
        item.setEnabled(True)

    # endregion
