from PySide2 import QtWidgets, QtGui, QtCore
from .browse_widget import BrowseWidget
import dpm.models as models
from .collection import IconCollection


class ListObjectsWidget(QtWidgets.QWidget):

    row_selected = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._columns = [
            {"field": "id", "header": "Node_ID", "width": 150, "hidden": True},
            {"field": "name", "header": "Название", "width": 500, "hidden": False},
            {"field": "last_update", "header": "Последнее обновление", "width": 350, "hidden": False},
            {"field": "last_revision", "header": "Анализ связей", "width": 250, "hidden": False}
        ]
        self.setLayout(QtWidgets.QVBoxLayout())
        self.model = None
        self.view = None
        self.selected_id = None

    def _process_row_selection(self):
        """
        Реакция на выбор строки в таблице
        """
        row_num = self.view.selectionModel().selectedRows()[0].row()
        self.selected_id = int(self.model.data(self.model.index(row_num, 0)))
        self.row_selected.emit()

    def _fill_table(self, dataset):
        row_count = len(dataset)
        self.model = QtGui.QStandardItemModel(row_count, len(self._columns))
        self.model.setHorizontalHeaderLabels([c["header"] for c in self._columns])
        for row in range(row_count):
            for column in range(len(self._columns)):
                # ToDo надо конвертировать дату в нормальный формат
                item = QtGui.QStandardItem(str(getattr(dataset[row], self._columns[column]["field"])))
                self.model.setItem(row, column, item)

        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)
        # по умолчанию сортируем по имени
        self.model.sort(1)
        # присоединяем сигнал для оповещения о выделении строки
        self.view.selectionModel().selectionChanged.connect(self._process_row_selection)
        # ToDo make ralative column width
        for column in range(len(self._columns)):
            self.view.setColumnWidth(column, self._columns[column]["width"])
            self.view.setColumnHidden(column, self._columns[column]["hidden"])

        self.layout().addWidget(self.view)

    def load_data(self, dataset):
        self.empty = (dataset is None or len(dataset) == 0)
        if not self.empty:
            self._fill_table(dataset)

class BrowseObjectWidget(BrowseWidget):
    """
    Виджет для просмотра внутренностей сложного объекта: базы данных, арма или всей системы в целом.

    Виджет содержит область с вкладками, каждая вкладка отвечает за определённую категоию вложенных объектов;
    На каждой вкладке - таблица объектов определённой категории.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._categories = []
        self.tab_pane = QtWidgets.QTabWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tab_pane)
        self.setLayout(layout)
    
    def _extract_selected_node(self):
        """
        По id находит выбранную ноду в списке orm-моделей.
        """
        tab_index = self.tab_pane.currentIndex()
        node_id = self.tab_pane.currentWidget().selected_id
        dataset = self._categories[tab_index]["dataset"]
        for item in dataset:
            if item.id == node_id:
                return item

    def _process_node_selection(self):
        """
        Обработчик сигнала выбора строки в таблице.
        """
        node = self._extract_selected_node()
        self._set_selected_node(node)

    def load_data(self, dataset):
        self._categories = dataset
        for category in self._categories:
            list_pane = ListObjectsWidget()
            list_pane.load_data(category["dataset"])
            # присоединяем сигнал для реакции на выбор строки в таблице
            list_pane.row_selected.connect(self._process_node_selection)
            # ToDo при переключении вкладок надо сбрасывать выбранную вершину
            self.tab_pane.addTab(list_pane, category["name"])

    def query_system_data(self):
        if self._storage is None:
            return
        dataset = [
            {
                "name": "АРМы",
                "dataset": self._storage.get_applications_list()
            },
            {
                "name": "Базы",
                "dataset": self._storage.get_databases_list()
            }
        ]
        self.observed_node = None
        self.selected_node = None
        self.load_data(dataset)

    def query_node_data(self, node):
        if self._storage is None:
            return
        if not hasattr(node, "categories"):
            raise Exception(f"Обзор объектов {node.__class__.__name__} не поддерживается.")
        self.observed_node = node
        self.selected_node = None
        self.load_data(self.observed_node.categories)

    def clear(self):
        """
        Очистить все вкладки, очистить категории, сбросить выбранную ноду
        """
        for index in range(len(self._categories)):
            widget = self.tab_pane.widget(index)
            self.tab_pane.removeTab(index)
            widget.close()
            widget.deleteLater()
        self._categories = []
        self.observed_node = None
        self._set_selected_node(None)
