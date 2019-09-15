from dpm.graphsworks import DpmGraph, NodeStatus
from PySide2 import QtWidgets, QtGui, QtCore
from .collection import IconCollection


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
    
    @classmethod
    def table_columns(cls):
        return [
            {"header": "Тип объекта", "width": 35, "hidden": False},
            {"header": "ID", "width": 100, "hidden": True},
            {"header": "Имя", "width": 400, "hidden": False},
            {"header": "Статус", "width": 100, "hidden": True},
        ]
    
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
    
    def _refresh_table_model(self):
        """
        Полностью обновляет табличную модель на основе графа.
        """
        print("_refresh_table_model")
        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels([c["header"] for c in HistoryPoint.table_columns()])
        for node in self.graph.nodes:
            if node == self.graph.pov_id:
                continue
            icon = QtGui.QStandardItem(IconCollection.get_icon_for_node_class(self.graph[node]["node_class"]), "")
            id = QtGui.QStandardItem(str(self.graph[node]["id"]))
            name = QtGui.QStandardItem(self.graph[node]["label"])
            status = QtGui.QStandardItem(str(int(self.graph[node]["status"])))
            model.appendRow([icon, id, name, status])
        for row in range(model.rowCount()):
            if int(model.data(model.index(row, self.STATUS_COLUMN_INDEX))) == NodeStatus.ROLLED_UP:
                self._paint_row_as_rolled_up(row)
        self.table_model = model
    
    def _refresh_tree_model(self):
        """
        Конвертирует граф в древовидную модель для виджета.
        """
        # черновой вариант
        """
        tree_model = QtGui.QStandardItemModel()
        root_item = tree_model.invisibleRootItem()

        item_up = QtGui.QStandardItem("Вверх")
        item_down = QtGui.QStandardItem("Вниз")
        root_item.appendRow(item_up)
        root_item.appendRow(item_down)

        for i in range(3):
            # без дублирования нельзя, иначе добавится только в одно место
            new_item1 = QtGui.QStandardItem(f"{i+1}")
            new_item2 = QtGui.QStandardItem(f"{i+4}")
            item_up.appendRow(new_item1)
            item_down.appendRow(new_item2)
        """
        pass
    
    def _paint_row_as_rolled_up(self, row):
        for column in range(len(HistoryPoint.table_columns())):
            self.active_model.setData(
                self.active_model.index(row, column), 
                QtGui.QBrush(QtCore.Qt.lightGray),
                QtCore.Qt.BackgroundRole
            )
    
    def _paint_row_as_visible(self, row):
        for column in range(len(HistoryPoint.table_columns())):
            self.active_model.setData(
                self.active_model.index(row, column), 
                QtGui.QBrush(QtCore.Qt.white), 
                QtCore.Qt.BackgroundRole
            )

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
    

    