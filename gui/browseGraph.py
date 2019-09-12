from PySide2 import QtWidgets, QtGui, QtCore
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from .browse_widget import BrowseWidget
import os
import settings
from dpm.graphsworks import DpmGraph
from .collection import IconCollection


class BrowseGraphWidget(BrowseWidget):
    """
    Большой виджет, отвечающий за работу с графом зависимостей.
    """
    # ToDo древовидная модель
    # ToDo событие выбора ноды в списке и его передача наверх
    # ToDo переход к новой точке отсчёта
    # ToDo экспорт графа в другие форматы
    # ToDo зависимость модели от чекбокса группировки
    # ToDo узнать, можно ли добавить зум и другие плюшки
    # ToDo надо увеличить размер области рисования, чтобы она занимала всё окно
    # ToDo создать класс HistoryPoint для описания элементов pov_history
    # ToDo создать самодельный класс модели данных, чтобы не перекрашивать строки руками
    # ToDo True и пустая строка в ячейке - слишком костыльное решение

    _table_columns = [
        {"header": "Тип объекта", "width": 35, "hidden": False},
        {"header": "ID", "width": 100, "hidden": True},
        {"header": "Имя", "width": 400, "hidden": False},
        {"header": "Скрыто", "width": 100, "hidden": True},
        {"header": "Скрыто пользователем", "width": 100, "hidden": True},
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
        self._init_node_context_menu()


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
        grid.addWidget(self.pov_icon, 0, 0)
        # имя точки отсчёта
        self.pov_label = QtWidgets.QLabel()
        grid.addWidget(self.pov_label, 0, 1)
        # стрелки
        # в начало
        self.pov_first = QtWidgets.QPushButton()
        self.pov_first.setIcon(IconCollection.pixmaps["begin"])
        grid.addWidget(self.pov_first, 0, 2)
        # назад
        self.pov_back = QtWidgets.QPushButton()
        self.pov_back.setIcon(IconCollection.pixmaps["back"])
        grid.addWidget(self.pov_back, 0, 3)
        # вперёд
        self.pov_forward = QtWidgets.QPushButton()
        self.pov_forward.setIcon(IconCollection.pixmaps["forward"])
        grid.addWidget(self.pov_forward, 0, 4)
        # в конец
        self.pov_last = QtWidgets.QPushButton()
        self.pov_last.setIcon(IconCollection.pixmaps["end"])
        grid.addWidget(self.pov_last, 0, 5)

        self.pov_first.clicked.connect(lambda: self._change_pov(self.pov_first))
        self.pov_back.clicked.connect(lambda: self._change_pov(self.pov_back))
        self.pov_forward.clicked.connect(lambda: self._change_pov(self.pov_forward))
        self.pov_last.clicked.connect(lambda: self._change_pov(self.pov_last))

        groupbox = QtWidgets.QGroupBox("Точка отсчёта")
        groupbox.setLayout(grid)
        groupbox.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.control_panel.layout().addWidget(groupbox)
    
    def _init_node_context_menu(self):
        self.node_context_menu = QtWidgets.QMenu()

        self.node_action_set_pov = QtWidgets.QAction(IconCollection.icons["new_pov"], "Сделать точкой отсчёта")
        self.node_action_set_pov.triggered.connect(self._make_new_pov)

        self.node_action_hide = QtWidgets.QAction(IconCollection.icons["invisible"], "Скрыть")
        self.node_action_hide.triggered.connect(self._hide_node)

        self.node_action_show = QtWidgets.QAction(IconCollection.icons["visible"], "Показать")
        self.node_action_show.triggered.connect(self._show_node)

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
    
    def _show_node_context_menu(self, position):
        self.node_context_menu.clear()
        self.node_context_menu.addAction(self.node_action_set_pov)
        # если нода видимая, то добавляем в меню пункт "Скрыть"
        # иначе добавляем пункт "Показать"
        row_num = self.table_view.selectionModel().selectedRows()[0].row()
        model = self.table_view.model()
        hidden_by_user = bool(model.data(model.index(row_num, 4)))
        if hidden_by_user:
            self.node_context_menu.addAction(self.node_action_show)
        else:
            self.node_context_menu.addAction(self.node_action_hide)
        
        self.node_context_menu.exec_(self.table_view.viewport().mapToGlobal(position))

    def _init_node_list(self):
        """
        Инициализирует виджеты, отвечающие за вывод списка вершин графа.
        При включении группировки ставится дерево, при отключении - таблица.
        """
        self.node_list = QtWidgets.QStackedWidget()

        self.tree_view = QtWidgets.QTreeView()

        self.table_view = QtWidgets.QTableView()
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_node_context_menu)

        self.node_list.addWidget(self.tree_view)
        self.node_list.addWidget(self.table_view)
        self.node_list.setCurrentIndex(self.node_list.indexOf(self.table_view))

        self.control_panel.layout().addWidget(self.node_list)

        self.number_of_nodes = QtWidgets.QLabel(f"Объектов: ")
        self.control_panel.layout().addWidget(self.number_of_nodes)

    def _set_table_model(self, model):
        """
        Устанавливает табличную модель для виджета со списком вершин графа.
        """
        self.table_view.setModel(model)
        self.table_view.horizontalHeader().hide()
        for column in range(len(self._table_columns)):
            self.table_view.setColumnWidth(column, self._table_columns[column]["width"])
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
        current_graph = history_point["graph"]
        self._set_table_model(history_point["table_model"])
        self._set_tree_model(history_point["tree_model"])

        # считываем из текущего графа параметры загрузки зависимостей
        # и ставим их в элементы управления на форме
        self.chb_down.setChecked(current_graph.reached_bottom_limit)
        self.chb_up.setChecked(current_graph.reached_upper_limit)
        self.spb_down.setValue(current_graph.levels_down)
        self.spb_up.setValue(current_graph.levels_up)
        # количество объектов (под списком)
        self.number_of_nodes.setText(f"Объектов: {history_point['table_model'].rowCount()}")
        # иконка pov-вершины
        self.pov_icon.setPixmap(
            IconCollection.get_pixmap_for_node_class(
                current_graph[current_graph.pov_id]["node_class"]
            )
        )
        self.pov_label.setText(current_graph[current_graph.pov_id]["label"])
        

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
        self._draw_current_graph()

    def _draw_current_graph(self):
        """
        Отображает текущий граф в области для рисования.
        """
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

    def _make_new_pov(self):
        print(f"make new pov")
        # self.current_history_pos += 1
        # self._read_graph_from_history()
        # self._toggle_pov_navigation_buttons()
    
    def _hide_node(self):
        row_num = self.table_view.selectionModel().selectedRows()[0].row()
        model = self.table_view.model()
        node_id = int(model.data(model.index(row_num, 1)))
        # модифицируем модель данных, чтобы указать, что нода спрятана пользователем
        model.setData(model.index(row_num, 3), "True")
        model.setData(model.index(row_num, 4), "True")
        # красим строку
        for column in range(len(self._table_columns)):
            model.setData(model.index(row_num, column), QtGui.QBrush(QtCore.Qt.lightGray), QtCore.Qt.BackgroundRole)
        # прячем ноду в самом графе
        self.pov_history[self.current_history_pos]["graph"].hide_node(node_id)
        # прячем в списке те объекты, которые были скрыты автоматически
        nodes_to_hide = self.pov_history[self.current_history_pos]["graph"].auto_hidden_nodes
        for row in range(model.rowCount()):
            if int(model.index(row, 1).data()) in nodes_to_hide:
                model.setData(model.index(row, 3), "True")
                self.table_view.setRowHidden(row, True)
        nodes_total = self.pov_history[self.current_history_pos]["graph"].number_of_subordinate_nodes
        self.number_of_nodes.setText(f"Объектов: {nodes_total - len(nodes_to_hide)}")
        # перерисовываем граф
        self._draw_current_graph()
    
    def _show_node(self):
        row_num = self.table_view.selectionModel().selectedRows()[0].row()
        model = self.table_view.model()
        node_id = int(model.data(model.index(row_num, 1)))
        # модифицируем модель данных, чтобы указать, что нода снова видима
        model.setData(model.index(row_num, 3), "")
        model.setData(model.index(row_num, 4), "")
        # красим строку обратно
        for column in range(len(self._table_columns)):
            model.setData(model.index(row_num, column), QtGui.QBrush(QtCore.Qt.white), QtCore.Qt.BackgroundRole)
        # обрабатываем граф
        self.pov_history[self.current_history_pos]["graph"].show_node(node_id)
        # показываем в списке те ноды, которые должны стать видимыми
        nodes_to_hide = self.pov_history[self.current_history_pos]["graph"].auto_hidden_nodes
        for row in range(model.rowCount()):
            if int(model.index(row, 1).data()) not in nodes_to_hide:
                model.setData(model.index(row, 3), "")
                self.table_view.setRowHidden(row, False)
        nodes_total = self.pov_history[self.current_history_pos]["graph"].number_of_subordinate_nodes
        self.number_of_nodes.setText(f"Объектов: {nodes_total - len(nodes_to_hide)}")
        # перерисовываем граф
        self._draw_current_graph()

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
            if node == graph.pov_id:
                continue
            icon = QtGui.QStandardItem(self._get_icon_for_node_class(graph[node]["node_class"]), "")
            id = QtGui.QStandardItem(str(graph[node]["id"]))
            name = QtGui.QStandardItem(graph[node]["label"])
            hidden = QtGui.QStandardItem("True" if graph[node]["hidden"] else "")
            hidden_by_user = QtGui.QStandardItem("True" if graph[node]["hidden_by_user"] else "")
            model.appendRow([icon, id, name, hidden, hidden_by_user])
        return model

    def _get_icon_for_node_class(self, node_class):
        """
        Подбирает иконку для отображения ноды в списке в зависимости от класса ноды.
        """
        return IconCollection.get_icon_for_node_class(node_class)

    # public methods
    
    def query_node_data(self, node):
        if self._session is None:
            return
        self.observed_node = node
        new_graph = DpmGraph(self._session, node)
        
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

