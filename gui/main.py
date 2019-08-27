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
        self._container = QtWidgets.QStackedWidget()
        self._browse_system_widget = BrowseObjectWidget()
        self._browse_object_widget = BrowseObjectWidget() # ToDo non identic widgets
        self._browse_graph_widget = BrowseGraphWidget()
        for widget in self._browse_widgets():
            self._container.addWidget(widget)
        self._container.currentChanged.connect(
            lambda: self._browse_widget_changed(self._container.currentIndex())
        )
        self.setCentralWidget(self._container)

        # по умолчанию главное окно находится в режиме обзора системы
        self._switch_to_system()
        self._browse_widget_changed(self._container.indexOf(self._browse_system_widget))

        self._selected_node = None

    def _browse_widgets(self):
        """
        Возвращает список обзорных виджетов.
        """
        return [
            self._browse_system_widget,
            self._browse_object_widget,
            self._browse_graph_widget
        ]

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
        """
        Включает режим обзора системы
        """
        index = self._container.indexOf(self._browse_system_widget)
        self._container.setCurrentIndex(index)

    def _switch_to_object(self):
        """
        Включает режим обзора объекта.
        """
        # ToDo self._selected_object needed to activate browse widget
        index = self._container.indexOf(self._browse_object_widget)
        self._container.setCurrentIndex(index)

    def _switch_to_graph(self):
        """
        Включает режим просмотра графа зависимостей.
        """
        index = self._container.indexOf(self._browse_graph_widget)
        self._container.setCurrentIndex(index)

    def _browse_widget_changed(self, index):
        """
        Прячет кнопки режимов просмотра в зависимости от того, какой
        из виджетов сейчас активен.
        """
        self._actions["browse_system"].setEnabled(
            index != self._container.indexOf(self._browse_system_widget)
        )
        self._actions["browse_object"].setEnabled(
            index != self._container.indexOf(self._browse_object_widget)
        )
        self._actions["browse_graph"].setEnabled(
            index != self._container.indexOf(self._browse_graph_widget)
        )

    def _init_toolbar(self):
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
        self._session = session
        for widget in self._browse_widgets():
            widget.set_session(self._session)

    def load_data(self, dataset):
        self.centralWidget().load_data(dataset)

    def query_system_data(self):
        """
        Запрашивает данные для обзора всей системы.
        """
        # не идёт дальше, если не задана сессия или
        # активен виджет, отличный от виджета обзора системы
        if getattr(self, "_session") is None:
            return
        if self._container.currentIndex() != self._container.indexOf(self._browse_system_widget):
            return
        self._browse_system_widget.query_system_data()


def init_gui(session):
    # ToDo это временная функция для тестирования формирования интерфейса
    app = QtWidgets.QApplication([])
    # сюда надо передавать категории из обзора системы: армы и базы
    # с одной стороны, надо передать, с другой - интерфейс должен быть независим от данных
    # в том смысле, что он не должен ничего сам запрашивать, вся
    # функциональность по работе с бд должна быть вытащена вовне
    main_window = DpmMainWindow()
    main_window.set_session(session)
    main_window.query_system_data()
    main_window.showMaximized()
    sys.exit(app.exec_())
    return main_window


if __name__ == "__main__":
    init_gui(None)
