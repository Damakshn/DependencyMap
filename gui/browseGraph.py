from PySide2 import QtWidgets, QtGui
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from .browse_widget import BrowseWidget
import os
import settings

icons_for_nodes = {}

class BrowseGraphWidget(BrowseWidget):
    """
    Большой виджет, отвечающий за работу с графом зависимостей.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_history_pos = 0
        self.pov_history = []

        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 1)

        self.setLayout(grid)
        self._init_draw_area()
        self._init_control_panel()

    def _init_draw_area(self):
        self.figure = plt.figure()
        self.draw_area = FigureCanvas(self.figure)
        self.draw_area.setStyleSheet("background-color: #FFFFE0;")
        self.layout().addWidget(self.draw_area, 0, 0)

    def _init_control_panel(self):
        # Панель управления отображением графа и содержащая список объектов.
        self.control_panel = QtWidgets.QWidget()
        self.control_panel.setLayout(QtWidgets.QVBoxLayout())
        # виджеты панели управления
        self._init_pov_panel()
        self._init_dependencies_panel()
        self._init_list_control_panel()
        self._init_node_list()

        self.layout().addWidget(self.control_panel, 0, 1)

    def _init_pov_panel(self):
        # панель для вывода точки отсчёта (point of view)
        # и перехода между точками отсчёта вперёд-назад
        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 4)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(4, 1)
        grid.setColumnStretch(5, 1)
        # иконка точки отсчёта
        self.pov_icon = QtWidgets.QLabel()
        self.pov_icon.setPixmap(QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/package.jpg")))
        grid.addWidget(self.pov_icon, 0, 0)
        # имя точки отсчёта
        self.pov_label = QtWidgets.QLabel()
        self.pov_label.setText("Это точка отсчёта")
        grid.addWidget(self.pov_label, 0, 1)
        # стрелки
        # в начало
        self.pov_first = QtWidgets.QPushButton()
        self.pov_first.setIcon(QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/begin32.png")))
        grid.addWidget(self.pov_first, 0, 2)
        # назад
        self.pov_back = QtWidgets.QPushButton()
        self.pov_back.setIcon(QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/back32.png")))
        grid.addWidget(self.pov_back, 0, 3)
        # вперёд
        self.pov_forward = QtWidgets.QPushButton()
        self.pov_forward.setIcon(QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/forward32.png")))
        grid.addWidget(self.pov_forward, 0, 4)
        # в конец
        self.pov_last = QtWidgets.QPushButton()
        self.pov_last.setIcon(QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/end32.png")))
        grid.addWidget(self.pov_last, 0, 5)

        self.pov_first.clicked.connect(lambda: self._change_pov(self.pov_first))
        self.pov_back.clicked.connect(lambda: self._change_pov(self.pov_back))
        self.pov_forward.clicked.connect(lambda: self._change_pov(self.pov_forward))
        self.pov_last.clicked.connect(lambda: self._change_pov(self.pov_last))

        groupbox = QtWidgets.QGroupBox("Точка отсчёта")
        groupbox.setLayout(grid)
        groupbox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.control_panel.layout().addWidget(groupbox)

    def _init_dependencies_panel(self):
        # панель управления подгрузкой зависимостей
        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 4)

        lb_up = QtWidgets.QLabel("Вверх")
        lb_down = QtWidgets.QLabel("Вниз")
        self.spb_up = QtWidgets.QSpinBox()
        self.spb_down = QtWidgets.QSpinBox()
        self.spb_up.setRange(0, 100)
        self.spb_down.setRange(0, 100)

        self.spb_up.setValue(0)
        self.spb_down.setValue(3)

        self.chb_up = QtWidgets.QCheckBox("До конца")
        self.chb_down = QtWidgets.QCheckBox("До конца")

        self.bt_load = QtWidgets.QPushButton("Загрузить")
        self.bt_load.clicked.connect(self._reload_dependencies)

        grid.addWidget(lb_up, 0, 0)
        grid.addWidget(self.spb_up, 0, 1)
        grid.addWidget(self.chb_up, 0, 2)

        grid.addWidget(lb_down, 1, 0)
        grid.addWidget(self.spb_down, 1, 1)
        grid.addWidget(self.chb_down, 1, 2)
        grid.addWidget(self.bt_load, 0, 3, 2, 1)
        panel = QtWidgets.QWidget()
        panel.setLayout(grid)
        panel.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.control_panel.layout().addWidget(panel)

    def _init_list_control_panel(self):
        # панель управления списком объектов (поиск и группировка)
        lb_search = QtWidgets.QLabel("Поиск:")
        self.le_search = QtWidgets.QLineEdit()
        self.le_search.returnPressed.connect(self._search_node_in_list)
        self.chb_grouping = QtWidgets.QCheckBox("Группировка")
        self.chb_grouping.stateChanged.connect(self._toggle_grouping)

        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 5)

        grid.addWidget(lb_search, 0, 0)
        grid.addWidget(self.le_search, 0, 1)
        grid.addWidget(self.chb_grouping, 1, 0, 1, 2)

        panel = QtWidgets.QWidget()
        panel.setLayout(grid)
        panel.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.control_panel.layout().addWidget(panel)

    def _init_node_list(self):
        # список вершин графа
        # ToDo зависимость от чекбокса группировки
        """
        TBD датасет хранится где-то отдельно от виджета?
        TBD виджет со списком как контейнер, в него кладётся конкретное представление?
        При включении группировки ставится дерево, при отключении - таблица
        """
        # черновой вариант
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

        tree_view = QtWidgets.QTreeView()
        tree_view.setModel(tree_model)
        tree_view.header().hide()
        
        self.control_panel.layout().addWidget(tree_view)

    def _reload_dependencies(self):
        print("reload dependencies")
        levels_up = self.spb_up.value()
        levels_down = self.spb_down.value()
        self.pov_history[self.current_history_pos]["graph"].load_dependencies(levels_up=levels_up, levels_down=levels_down)
        self._draw_current_graph()

    def _draw_current_graph(self):
        # ToDo разобраться, как работает визуализация, что откуда надо вызывать, что куда передавать, что для чего надо
        print("draw current graph")
        self.figure.clf()
        """
        nx.draw(B, pos=pos, with_labels=True)
        self.canvas.draw_idle()
        """

    def _read_graph_from_history(self):
        """
        Читает граф из текущей позиции в истории, заполняет значения виджетов значениями
        из атрибутов графа и выводит граф в области для отображения.
        """
        print("read graph from history")
        self._draw_current_graph()

    def _change_pov(self, button):
        """
        движение по истории точек отсчёта
        в зависимости от того, какая кнопка была нажата, двигается вперёд, назада, в начало или в конец
        если достигнуто начало истории просмотров, то кнопки "в начало" и "назад" выключаются, если 
        достигнут конец, то выключаются кнопки "Вперёд" и "в конец".
        """
        print("change pov via button")
        if button == self.pov_first:
            self.current_history_pos = 0
        elif button == self.pov_back:
            self.current_history_pos -= 1
        elif button == self.pov_forward:
            self.current_history_pos += 1
        elif button == self.pov_last:
            self.current_history_pos = (len(self.pov_history) - 1)

        self._disable_pov_navigation_buttons()

        self._read_graph_from_history()

    def _disable_pov_navigation_buttons(self):
        print("disable pov navigation buttons")
        not_begin = (self.current_history_pos != 0)
        not_end = (self.current_history_pos != (len(self.pov_history) - 1))
        self.pov_first.setEnabled(not_begin)
        self.pov_back.setEnabled(not_begin)
        self.pov_forward.setEnabled(not_end)
        self.pov_last.setEnabled(not_end)

    def _toggle_grouping(self):
        print(f"toggle grouping {self.chb_grouping.isChecked()}")

    def _search_node_in_list(self):
        print(f"search for {self.le_search.text()}")

    def _make_new_pov(self, node_id):
        print(f"make new pov {node_id}")
        self.current_history_pos += 1
        self._read_graph_from_history()
        self._disable_pov_navigation_buttons()
    
    # public methods
    
    def load_data(self, graph):
        """
        Инициализирует данные виджета.
        """
        # todo delete later, when proper graph will be prepared
        self.pov_history.append({"graph": graph})
        self._disable_pov_navigation_buttons()
        self._reload_dependencies()
    
    def query_node_data(self, node):
        if self._session is None:
            return
        self.observed_node = node



class TableNodeList(QtWidgets.QTableView):
    """
    Список объектов в виде таблицы

    Настройка:
        заголовка нет
        2 колонки, первая узкая, вторая на всю оставшуюся ширину
        1 колонка для иконки (создаётся специальный виджет), вторая для названия
        вызов контекстного меню для каждой строки
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


def convert_graph_to_table_model(graph):
    return None


def convert_graph_to_tree_model(graph):
    return None
