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
        self.selected_node = None

        self._browse_system_widget = BrowseObjectWidget()
        self._browse_system_widget.node_selected.connect(self._select_node)

        self._browse_object_widget = BrowseObjectWidget()
        self._browse_object_widget.node_selected.connect(self._select_node)

        self._browse_graph_widget = BrowseGraphWidget()
        self._browse_graph_widget.node_selected.connect(self._select_node)

        for widget in self._browse_widgets():
            self._container.addWidget(widget)
        self._container.currentChanged.connect(self._browse_widget_changed)
        self.setCentralWidget(self._container)

        # по умолчанию главное окно находится в режиме обзора системы
        self._switch_to_system()
        self._browse_widget_changed()
    
    # методы инициализации
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

    # прочие методы
    def _browse_widgets(self):
        """
        Возвращает список обзорных виджетов.
        """
        return [
            self._browse_system_widget,
            self._browse_object_widget,
            self._browse_graph_widget
        ]

    def _select_node(self):
        """
        Обработчик выбора определённой ноды в виджете обзора.
        """
        self.selected_node = self._container.currentWidget().selected_node
        self._toggle_toolbar_actions()
    
    # ToDo какая-то проблема с переключением кнопок, при многократных нажатиях всё сыпется
    def _switch_to_system(self):
        """
        Включает режим обзора системы
        """
        index = self._container.indexOf(self._browse_system_widget)
        self.selected_node = self._browse_system_widget.selected_node
        self._container.setCurrentIndex(index)

    def _switch_to_object(self):
        """
        Включает режим обзора объекта.
        """
        self._browse_object_widget.clear()
        # надо завязать на виджет обзора
        node = self.selected_node
        self.selected_node = None
        index = self._container.indexOf(self._browse_object_widget)
        # при углублённом просмотре не происходит смены индекса, а значит не прокает переключение кнопок
        self._container.setCurrentIndex(index)
        self._browse_object_widget.query_node_data(node)

    def _switch_to_graph(self):
        """
        Включает режим просмотра графа зависимостей.
        """
        index = self._container.indexOf(self._browse_graph_widget)
        self._container.setCurrentIndex(index)
    
    def _toggle_toolbar_actions(self):
        """
        Прячет кнопки режимов просмотра в зависимости от того, какой
        из виджетов обзора сейчас активен и выбрана ли в нём сейчас какая-нибудь
        нода.
        """
        print(self.selected_node)
        index = self._container.currentIndex()
        self._actions["browse_system"].setEnabled(
            index != self._container.indexOf(self._browse_system_widget)
        )
        self._actions["browse_object"].setEnabled(
            self.selected_node is not None
            and hasattr(self.selected_node, "categories")
        )
        self._actions["browse_graph"].setEnabled(
            self.selected_node is not None
        )

    def _browse_widget_changed(self):
        self._toggle_toolbar_actions()

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
