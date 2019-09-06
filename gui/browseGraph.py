from PySide2 import QtWidgets, QtGui
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from .browse_widget import BrowseWidget
import os
import settings
from dpm.graphsworks import DpmGraph

icons_for_nodes = {}

class BrowseGraphWidget(BrowseWidget):
    """
    Большой виджет, отвечающий за работу с графом зависимостей.
    """

    _table_columns = [
            {"header": "Тип объекта", "width_in_percent": 20, "hidden": False},
            {"header": "ID", "width_in_percent": 0, "hidden": True},
            {"header": "Имя", "width_in_percent": 80, "hidden": False}
        ]

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
        self.canvas = FigureCanvas(self.figure)
        self.layout().addWidget(self.canvas, 0, 0)


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
        """
        Инициализирует виджеты, отвечающие за вывод списка вершин графа.
        При включении группировки ставится дерево, при отключении - таблица.
        """
        # ToDo зависимость от чекбокса группировки
        self.node_list = QtWidgets.QStackedWidget()

        self.tree_view = QtWidgets.QTreeView()

        self.table_view = QtWidgets.QTableView()
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.node_list.addWidget(self.tree_view)
        self.node_list.addWidget(self.table_view)
        self.node_list.setCurrentIndex(self.node_list.indexOf(self.table_view))

        self.control_panel.layout().addWidget(self.node_list)
    
    def _set_table_model(self, model):
        """
        Устанавливает табличную модель для виджета со списком вершин графа.
        """
        self.table_view.setModel(model)
        self.table_view.horizontalHeader().hide()
        for column in range(len(self._table_columns)):
            # ToDo с шириной виджета какая-то ерунда, надо убрать горизонтальную прокрутку
            self.table_view.setColumnWidth(column, self._table_columns[column]["width_in_percent"] / 100 * self.table_view.width())
            self.table_view.setColumnHidden(column, self._table_columns[column]["hidden"])

    def _set_tree_model(self, model):
        """
        Устанавливает древовидную модель для виджета со списком вершин графа.
        """
        self.tree_view.setModel(model)
        self.tree_view.header().hide()
    
    def _read_graph_from_history(self):
        """
        Читает граф из текущей позиции в истории, заполняет значения виджетов значениями
        из атрибутов графа и выводит граф в области для отображения.
        """
        history_point = self.pov_history[self.current_history_pos]
        self._set_table_model(history_point["table_model"])
        self._set_tree_model(history_point["tree_model"])

        # считываем из текущего графа параметры загрузки зависимостей
        # и ставим их в элементы управления на форме
        self.chb_down.setChecked(history_point["graph"].reached_bottom_limit)
        self.chb_up.setChecked(history_point["graph"].reached_upper_limit)
        self.spb_down.setValue(history_point["graph"].levels_down)
        self.spb_up.setValue(history_point["graph"].levels_up)

        self._draw_current_graph()

    def _reload_dependencies(self):
        """
        Подгружает уровни зависимости объекта, изменяет текущий граф, изменяет модели
        для отображения списка в виде таблицы или дерева.
        """
        levels_up = self.spb_up.value()
        levels_down = self.spb_down.value()
        history_point = self.pov_history[self.current_history_pos]
        graph = history_point["graph"]
        graph.load_dependencies(levels_up=levels_up, levels_down=levels_down)
        history_point["table_model"] = self._convert_graph_to_table_model(graph)
        history_point["tree_model"] = None
        self._read_graph_from_history()

    def _draw_current_graph(self):
        """
        Отображает текущий граф в области для рисования.
        """
        # ToDo узнать, можно ли добавить зум и другие плюшки
        # ToDo надо увеличить размер области, чтобы она занимала всё окно
        self.figure.clf()
        self.pov_history[self.current_history_pos]["graph"].show()
        self.canvas.draw_idle()

    def _change_pov(self, button):
        """
        движение по истории точек отсчёта
        в зависимости от того, какая кнопка была нажата, двигается вперёд, назада, в начало или в конец
        если достигнуто начало истории просмотров, то кнопки "в начало" и "назад" выключаются, если 
        достигнут конец, то выключаются кнопки "Вперёд" и "в конец".
        """
        if button == self.pov_first:
            self.current_history_pos = 0
        elif button == self.pov_back:
            self.current_history_pos -= 1
        elif button == self.pov_forward:
            self.current_history_pos += 1
        elif button == self.pov_last:
            self.current_history_pos = (len(self.pov_history) - 1)

        self._toggle_pov_navigation_buttons()

        self._read_graph_from_history()

    def _toggle_pov_navigation_buttons(self):
        not_begin = (self.current_history_pos != 0)
        not_end = (self.current_history_pos != (len(self.pov_history) - 1))
        self.pov_first.setEnabled(not_begin)
        self.pov_back.setEnabled(not_begin)
        self.pov_forward.setEnabled(not_end)
        self.pov_last.setEnabled(not_end)

    def _toggle_grouping(self):
        pass

    def _search_node_in_list(self):
        pass

    def _make_new_pov(self, node_id):
        self.current_history_pos += 1
        self._read_graph_from_history()
        self._toggle_pov_navigation_buttons()
    
    def _set_dependencies_loading_levels(self):
        """
        По типу ноды определяем рекомендуемое количество уровней
        зависимостей для загрузки, выставляем виджеты управления 
        в соответствующее положение.
        """
        up, down = self.observed_node.get_recommended_loading_depth()

        if up == float("inf"):
            self.chb_up.setChecked(True)
        else:
            self.spb_up.setValue(up)

        if down == float("inf"):
            self.chb_down.setChecked(True)
        else:
            self.spb_down.setValue(down)

    def _convert_graph_to_tree_model(self, graph):
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
    
    def _convert_graph_to_table_model(self, graph):
        """
        Конвертирует граф в табличную модель для виджета.
        """
        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels([c["header"] for c in self._table_columns])
        for node in graph.nodes:
            icon = QtGui.QStandardItem(self._get_icon_for_node_class(graph[node]["node_class"]), "")
            id = QtGui.QStandardItem(str(graph[node]["id"]))
            name = QtGui.QStandardItem(graph[node]["label"])
            model.appendRow([icon, id, name])
        return model

    def _get_icon_for_node_class(self, node_class):
        """
        Подбирает иконку для отображения ноды в списке в зависимости от класса ноды.
        """
        # ToDo подобрать иконки на всё подряд и создать каталог
        return QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/table32.png"))

    # public methods
    
    def query_node_data(self, node):
        if self._session is None:
            return
        self.observed_node = node
        new_graph = DpmGraph(self._session, node)
        # ToDo создание модели происходит дальше, как-то не очень, может закатать всё в класс?
        self.pov_history.append(
            {
                "graph": new_graph,
                "table_model": None,
                "tree_model": None
            }
        )
        self._toggle_pov_navigation_buttons()
        self._set_dependencies_loading_levels()
        self._reload_dependencies()

class BrowseGraphHistoryPoint:
    pass
