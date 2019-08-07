from PySide2 import QtWidgets, QtGui

# --------------------------
# added for tests

icons_for_nodes = {}

class BrowseGraphWidget(QtWidgets.QWidget):
    """
    Большой виджет, отвечающий за работу с графом зависимостей.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # QGridLayout - graph to the left, panel to the right
        self.setLayout(QtWidgets.QGridLayout())
        self._init_draw_area()
        self._init_control_panel()

    def _init_draw_area(self):
        # ToDo пока используем болванку
        self.draw_area = QtWidgets.QWidget()
        self.layout().addWidget(self.draw_area, 0, 0)

    def _init_control_panel(self):
        # ToDo position - right side
        self.control_panel = GraphControlPanel()
        self.layout().addWidget(self.control_panel, 0, 1)

    def load_data(self):
        pass


class GraphControlPanel(QtWidgets.QWidget):
    """
    Панель управления отображением графа и содержащая список объектов.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLayout(QtWidgets.QVBoxLayout())
        
        self._init_pov_panel()
        self._init_dependencies_panel()
        self._init_list_control_panel()
        self._init_node_list()

    def _init_pov_panel(self):
        # панель для вывода точки отсчёта (point of view)
        # и перехода между точками отсчёта вперёд-назад
        # ToDo размеры колонок сетки с кнопками
        grid = QtWidgets.QGridLayout()
        # иконка объекта
        self.pov_icon = QtWidgets.QLabel()
        # event needed
        self.pov_icon.setPixmap(QtGui.QPixmap("assets/package.png"))
        grid.addWidget(self.pov_icon, 0, 0)
        # имя объекта
        self.pov_label = QtWidgets.QLabel()
        # event needed
        self.pov_label.setText("Это точка отсчёта")
        grid.addWidget(self.pov_label, 0, 1)
        # стрелки
        # в начало
        self.pov_first = QtWidgets.QPushButton()
        self.pov_first.setIcon(QtGui.QPixmap("assets/begin32.png"))
        grid.addWidget(self.pov_first, 0, 2)
        # назад
        self.pov_back = QtWidgets.QPushButton()
        self.pov_back.setIcon(QtGui.QPixmap("assets/back32.png"))
        grid.addWidget(self.pov_back, 0, 3)
        # вперёд
        self.pov_forward = QtWidgets.QPushButton()
        self.pov_forward.setIcon(QtGui.QPixmap("assets/forward32.png"))
        grid.addWidget(self.pov_forward, 0, 4)
        # в конец
        self.pov_last = QtWidgets.QPushButton()
        self.pov_last.setIcon(QtGui.QPixmap("assets/end32.png"))
        grid.addWidget(self.pov_last, 0, 5)

        groupbox = QtWidgets.QGroupBox("Точка отсчёта")
        groupbox.setLayout(grid)
        self.layout().addWidget(groupbox)

    def _init_dependencies_panel(self):
        # панель управления подгрузкой зависимостей
        # QGridLayout
        pass

    def _init_list_control_panel(self):
        # панель управления списком объектов (поиск и группировка)
        # QGridLayout
        pass

    def _init_node_list(self):
        # список вершин графа
        pass


class TableNodeList(QtWidgets.QTableView):
    """
    Список объектов в виде таблицы
    """
    pass


class TreeNodeList(QtWidgets.QTreeView):
    """
    Список объектов в виде дерева
    """
    pass


class NodeContextMenu(QtWidgets.QMenu):
    """
    Контекстное меню объекта (ноды графа)
    """
    pass
