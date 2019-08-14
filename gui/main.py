from PySide2 import QtWidgets, QtGui
import sys
from browseObject import BrowseObjectWidget
from browseGraph import BrowseGraphWidget

# --------------------------
# added for tests


class DpmMainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._icons = {}
        self.setWindowIcon(QtGui.QIcon("assets/system48.jpg"))
        self._init_toolbar_icons()
        self._init_toolbar()
        self._init_main_menu()
        self._init_status_bar()

        # по умолчанию главное окно находится в режиме обзора системы
        #browse_system_widget = BrowseObjectWidget()
        browse_graph_widget = BrowseGraphWidget()
        self.setCentralWidget(browse_graph_widget)

    def _init_toolbar_icons(self):
        self._icons = {
            "browse_system": QtWidgets.QAction(QtGui.QIcon("assets/system48.png"), "Обзор системы"),
            "browse_object":  QtWidgets.QAction(QtGui.QIcon("assets/list48.png"), "Обзор объекта"),
            "browse_graph":  QtWidgets.QAction(QtGui.QIcon("assets/network48.png"), "Просмотр зависимостей")
        }

    def _init_toolbar(self):
        # ToDo тулбар должен реагировать на смену центрального виджета и на смену выбранного объекта в нём
        toolbar = QtWidgets.QToolBar(self)
        toolbar.setMovable(False)
        toolbar.addAction(self._icons["browse_system"])
        toolbar.addAction(self._icons["browse_object"])
        toolbar.addAction(self._icons["browse_graph"])
        self.addToolBar(toolbar)

    def _init_main_menu(self):
        pass

    def _init_status_bar(self):
        # реагирует на смену центрального виджета и на некоторые другие события
        pass

    def load_data(self, dataset):
        self.centralWidget().load_data(dataset)


def init_gui():
    # ToDo это временная функция для тестирования формирования интерфейса
    app = QtWidgets.QApplication([])
    # сюда надо передавать категории из обзора системы: армы и базы
    # с одной стороны, надо передать, с другой - интерфейс должен быть независим от данных
    # в том смысле, что он не должен ничего сам запрашивать, вся
    # функциональность по работе с бд должна быть вытащена вовне
    main_window = DpmMainWindow()
    dataset = [
        {"name": "АРМы", "dataset": []},
        {"name": "Базы данных", "dataset": []}
    ]
    main_window.load_data(dataset=dataset)
    main_window.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    init_gui()
