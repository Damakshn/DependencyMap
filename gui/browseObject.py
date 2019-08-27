from PySide2 import QtWidgets, QtGui
from .browse_widget import BrowseWidget
import dpm.models as models


class ListObjectsWidget(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._columns = [
            {"field": "name", "header": "Название", "width": 500},
            {"field": "last_update", "header": "Последнее обновление", "width": 350},
            {"field": "last_revision", "header": "Анализ связей", "width": 250}
        ]
        self.setLayout(QtWidgets.QVBoxLayout())
        self.model = None
        self.view = None
        # ToDo add selected_node attribute

    def _fill_table(self, dataset):
        row_count = len(dataset)
        self.model = QtGui.QStandardItemModel(row_count, len(self._columns))
        self.model.setHorizontalHeaderLabels([c["header"] for c in self._columns])
        for row in range(row_count):
            for column in range(len(self._columns)):
                # ToDo move this to self._add_model_item_from_data_row
                # ToDo need to convert datetime to string properly
                item = QtGui.QStandardItem(str(getattr(dataset[row], self._columns[column]["field"])))
                self.model.setItem(row, column, item)

        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # ToDo make ralative column width
        for column in range(len(self._columns)):
            self.view.setColumnWidth(column, self._columns[column]["width"])

        self.layout().addWidget(self.view)
    
    def _add_model_item_from_data_row(self, row):
        pass

    def _show_empty_widget(self):
        pass

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
        self._categories = {}
        self.tab_pane = QtWidgets.QTabWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tab_pane)
        self.setLayout(layout)

    def load_data(self, dataset):
        self._categories = dataset
        for category in self._categories:
            list_pane = ListObjectsWidget()
            list_pane.load_data(category["dataset"])
            self.tab_pane.addTab(list_pane, category["name"])
    
    def query_system_data(self):
        if self._session is None:
            return
        dataset = [
            {
                "name": "АРМы",
                "dataset": self._session.query(models.Application).all()
            },
            {
                "name": "Базы",
                "dataset": self._session.query(models.Database).all()
            }
        ]
        self.load_data(dataset)
        
