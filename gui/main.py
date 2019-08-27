from PySide2 import QtWidgets, QtGui
import sys
from .browseObject import BrowseObjectWidget
from .browseGraph import BrowseGraphWidget
import settings
import os


class DpmMainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._icons = {}
        self._actions = {}
        self._init_icons()
        self._init_toolbar_actions()
        self.setWindowIcon(self._icons["program"])
        self._init_toolbar()
        self._init_main_menu()
        self._init_status_bar()
        self._browse_system_widget = BrowseObjectWidget()
        self._browse_object_widget = None
        self._browse_graph_widget = None # BrowseGraphWidget()

        # по умолчанию главное окно находится в режиме обзора системы
        self. _switch_to_system()

    def _init_icons(self):
        self._icons = {
            "program": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/system48.jpg")),
            "browse_system": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/system48.png")),
            "browse_object":  QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/list48.png")),
            "browse_graph":  QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/network48.png"))
        }

    def _init_toolbar_actions(self):
        self._actions = {
            "browse_system": QtWidgets.QAction(self._icons["browse_system"], "Обзор системы"),
            "browse_object":  QtWidgets.QAction(self._icons["browse_object"], "Обзор объекта"),
            "browse_graph":  QtWidgets.QAction(self._icons["browse_graph"], "Просмотр зависимостей")
        }
        # ToDo toggle actions instead of clicks
        self._actions["browse_system"].triggered.connect(self._switch_to_system)
        self._actions["browse_object"].triggered.connect(self._switch_to_object)
        self._actions["browse_graph"].triggered.connect(self._switch_to_graph)

    def _switch_to_system(self):
        # TBD RuntimeError: Internal C++ object (BrowseObjectWidget) already deleted
        # ToDo see https://doc.qt.io/archives/qt-4.8/qstackedwidget.html and dont use setCentralWidget
        if self._browse_system_widget is None:
            self._browse_system_widget = BrowseObjectWidget()
        self.setCentralWidget(self._browse_system_widget)

        self._actions["browse_system"].setEnabled(False)
        self._actions["browse_object"].setEnabled(True)
        self._actions["browse_graph"].setEnabled(True)

    def _switch_to_object(self):
        """
        if self._browse_object_widget is None:
            self._browse_object_widget = 
        """
        self._actions["browse_system"].setEnabled(True)
        self._actions["browse_object"].setEnabled(False)
        self._actions["browse_graph"].setEnabled(True)
        QtWidgets.QMessageBox.about(self, settings.PROJECT_NAME, "Обзор объекта")

    def _switch_to_graph(self):
        if self._browse_graph_widget is None:
            self._browse_graph_widget = BrowseGraphWidget()
        self.setCentralWidget(self._browse_graph_widget)

        self._actions["browse_system"].setEnabled(True)
        self._actions["browse_object"].setEnabled(True)
        self._actions["browse_graph"].setEnabled(False)

        QtWidgets.QMessageBox.about(self, settings.PROJECT_NAME, "Обзор графа")

    def _init_toolbar(self):
        # ToDo тулбар должен реагировать на смену центрального виджета и на смену выбранного объекта в нём
        toolbar = QtWidgets.QToolBar(self)
        toolbar.setMovable(False)
        toolbar.addAction(self._actions["browse_system"])
        toolbar.addAction(self._actions["browse_object"])
        toolbar.addAction(self._actions["browse_graph"])
        self.addToolBar(toolbar)

    def _init_main_menu(self):
        pass

    def _init_status_bar(self):
        # реагирует на смену центрального виджета и на некоторые другие события
        pass
    
    def set_session(self, session):
        self.session = session

    def load_data(self, dataset):
        self.centralWidget().load_data(dataset)


def init_gui(session):
    # ToDo это временная функция для тестирования формирования интерфейса
    app = QtWidgets.QApplication([])
    # сюда надо передавать категории из обзора системы: армы и базы
    # с одной стороны, надо передать, с другой - интерфейс должен быть независим от данных
    # в том смысле, что он не должен ничего сам запрашивать, вся
    # функциональность по работе с бд должна быть вытащена вовне
    main_window = DpmMainWindow()
    main_window.set_session(session)
    dataset = [
        {"name": "АРМы", "dataset": []},
        {"name": "Базы данных", "dataset": []}
    ]
    # ToDo надо как-то отделить интерфейс от всего этого
    """
    from dpm.graphsworks import DpmGraph
    from dpm.models import Node
    test_pov_node = session.query(Node).filter(Node.id == 2).one()
    test_graph = DpmGraph(session, test_pov_node)
    main_window.load_data(dataset=test_graph)
    """
    main_window.showMaximized()
    sys.exit(app.exec_())
    return main_window


if __name__ == "__main__":
    init_gui(None)
