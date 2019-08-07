from PySide2 import QtWidgets, QtGui


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

    def _fill_table(self, dataset):
        row_count = len(dataset)
        # ToDo ширина колонок
        self.model = QtGui.QStandardItemModel(row_count, len(self._columns))
        self.model.setHorizontalHeaderLabels([c["header"] for c in self._columns])
        for row in range(row_count):
            for column in range(len(self._columns)):
                item = QtGui.QStandardItem(getattr(dataset[row], self._columns[column]["field"]))
                #item = QtGui.QStandardItem(dataset[row][self._columns[column]["field"]])
                self.model.setItem(row, column, item)

        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        for column in range(len(self._columns)):
            self.view.setColumnWidth(column, self._columns[column]["width"])

        self.layout().addWidget(self.view)

    def _show_empty_widget(self):
        pass

    def load_data(self, dataset):
        self.empty = (dataset is None or len(dataset) == 0)
        if not self.empty:
            self._fill_table(dataset)

class BrowseObjectWidget(QtWidgets.QTabWidget):
    """
    Виджет для просмотра внутренностей сложного объекта: базы данных, арма или всей системы в целом.

    Виджет содержит область с вкладками, каждая вкладка отвечает за определённую категоию вложенных объектов;
    На каждой вкладке - таблица объектов определённой категории.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._categories = {}

    def load_data(self, dataset):
        self._categories = dataset
        for category in self._categories:
            list_pane = ListObjectsWidget()
            #list_pane.load_data(category["dataset"])
            list_pane.load_data(dataset=None)
            self.addTab(list_pane, category["name"])
        
