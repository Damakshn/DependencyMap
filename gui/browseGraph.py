from PySide2 import QtWidgets, QtGui, QtCore
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from .browse_widget import BrowseWidget
import os
import settings
from dpm.graphsworks import DpmGraph, NodeStatus
from .collection import IconCollection
from .historyPoint import HistoryPoint


class BrowseGraphWidget(BrowseWidget):
    """
    Большой виджет, отвечающий за работу с графом зависимостей.
    """
    # region ToDO
    # большие фичи интерфейса:
    #   ToDo скрытие объекта в древовидной модели (с закрашиванием)
    #   ToDo поиск
    #   ToDo фокус на объекте в таблице\дереве при поиске
    #   ToDo событие выбора ноды в списке и его передача наверх
    #   ToDo переход к новой точке отсчёта
    # структура кода
    #   ToDo убрать настройки колонок куда-нибудь
    # Область отображения:
    #   ToDo узнать, можно ли добавить зум и другие плюшки
    #   ToDo надо увеличить размер области рисования, чтобы она занимала всё окно
    # дополнения
    #   ToDo выводить количество объектов в списке в виде Объектов: *, отображается: *
    # на будущее
    #   ToDo экспорт графа в другие форматы
    # endregion

    _table_columns = [
        {"header": "Тип объекта", "width": 35, "hidden": False},
        {"header": "ID", "width": 100, "hidden": True},
        {"header": "Имя", "width": 400, "hidden": False},
        {"header": "Статус", "width": 100, "hidden": True},
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_history_pos = 0
        self.pov_history = []
        layout = QtWidgets.QVBoxLayout()

        self.setLayout(layout)
        self.splitter = QtWidgets.QSplitter()
        self.layout().addWidget(self.splitter)
        self._init_draw_area()
        self._init_control_panel()
        self._init_node_context_menu()

    # region initializers

    def _init_draw_area(self):
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.splitter.addWidget(self.canvas)

    def _init_control_panel(self):
        # Панель управления отображением графа и содержащая список объектов.
        self.control_panel = QtWidgets.QWidget()
        self.control_panel.setLayout(QtWidgets.QVBoxLayout())
        # виджеты панели управления
        self._init_pov_panel()
        self._init_dependencies_panel()
        self._init_list_control_panel()
        self._init_node_list()
        self.splitter.addWidget(self.control_panel)

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

        self.table_view.horizontalHeader().hide()
        self.table_view.verticalHeader().hide()

        """
        self.table_view.selectionModel().selectionChanged.connect(self._process_row_selection)
        self.tree_view.selectionModel().selectionChanged.connect(self._process_row_selection)
        """

        self.node_list.addWidget(self.tree_view)
        self.node_list.addWidget(self.table_view)
        self.node_list.setCurrentIndex(self.node_list.indexOf(self.table_view))

        self.control_panel.layout().addWidget(self.node_list)

        self.number_of_nodes = QtWidgets.QLabel(f"Объектов: ")
        self.control_panel.layout().addWidget(self.number_of_nodes)
    
    # endregion
    
    # region utility methods

    def _show_node_context_menu(self, position):
        self.node_context_menu.clear()
        self.node_context_menu.addAction(self.node_action_set_pov)
        # если нода видимая, то добавляем в меню пункт "Скрыть"
        # иначе добавляем пункт "Показать"
        row_num = self.table_view.selectionModel().selectedRows()[0].row()
        model = self.table_view.model()
        status = int(model.data(model.index(row_num, 3)))
        if status == NodeStatus.ROLLED_UP:
            self.node_context_menu.addAction(self.node_action_show)
        else:
            self.node_context_menu.addAction(self.node_action_hide)
        
        self.node_context_menu.exec_(self.table_view.viewport().mapToGlobal(position))
    
    def _process_row_selection(self):
        """
        row_num = self.view.selectionModel().selectedRows()[0].row()
        self.row_selected.emit()
        """
        row_num = self._active_view.selectionModel().selectedRows()[0].row()
        self.selected_id = int(self.model.data(self.model.index(row_num, 0)))

    def _set_table_model(self, model):
        """
        Устанавливает табличную модель для виджета со списком вершин графа.
        """
        self.table_view.setModel(model)
        for column in range(len(self._table_columns)):
            self.table_view.setColumnWidth(column, self._table_columns[column]["width"])
            self.table_view.setColumnHidden(column, self._table_columns[column]["hidden"])

    def _set_tree_model(self, model):
        """
        Устанавливает древовидную модель для виджета со списком вершин графа.
        """
        self.tree_view.setModel(model)
        for column in range(len(self._table_columns)):
            self.tree_view.setColumnHidden(column, self._table_columns[column]["hidden"])
    
    def _prepare_view(self):
        STATUS_COLUMN_INDEX = 3
        # прячем в списке те объекты, которые были скрыты автоматически
        model = self._active_view.model()
        for row in range(model.rowCount()):
            self.table_view.setRowHidden(
                row, 
                int(model.index(row, STATUS_COLUMN_INDEX).data()) == NodeStatus.AUTO_HIDDEN
            )
        self.number_of_nodes.setText(f"Объектов: {self.pov_history[self.current_history_pos].number_of_nodes_in_list}")
    
    def _read_graph_from_history(self):
        """
        Читает граф из текущей позиции в истории, заполняет значения виджетов значениями
        из атрибутов графа и выводит граф в области для отображения.
        """
        history_point = self.pov_history[self.current_history_pos]
        self._set_table_model(history_point.table_model)
        self._set_tree_model(history_point.tree_model)
        self.chb_grouping.setChecked(history_point.grouping)
        self._prepare_view()
        # считываем из текущего графа параметры загрузки зависимостей
        # и ставим их в элементы управления на форме
        self.chb_down.setChecked(history_point.reached_bottom_limit)
        self.chb_up.setChecked(history_point.reached_upper_limit)
        self.spb_down.setValue(history_point.levels_down)
        self.spb_up.setValue(history_point.levels_up)
        # количество объектов (под списком)
        self.number_of_nodes.setText(f"Объектов: {history_point.number_of_nodes_in_list}")
        # иконка pov-вершины
        self.pov_icon.setPixmap(
            IconCollection.get_pixmap_for_node_class(history_point.pov_node_class)
        )
        self.pov_label.setText(history_point.pov_node_label)
        self._draw_current_graph()

    def _reload_dependencies(self):
        """
        Подгружает уровни зависимости объекта, изменяет текущий граф, изменяет модели
        для отображения списка в виде таблицы или дерева.
        """
        levels_up = self.spb_up.value()
        levels_down = self.spb_down.value()
        history_point = self.pov_history[self.current_history_pos]
        QtGui.QGuiApplication.setOverrideCursor(QtGui.Qt.BusyCursor)
        history_point.load_dependencies(levels_up, levels_down)
        self._read_graph_from_history()
        self._draw_current_graph()
        QtGui.QGuiApplication.restoreOverrideCursor()

    def _draw_current_graph(self):
        """
        Отображает текущий граф в области для рисования.
        """
        self.figure.clf()
        self.pov_history[self.current_history_pos].show_graph()
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
        """
        Переключает группировку, подменяя виджеты и устанавливая активное представление
        """
        if self.chb_grouping.isChecked():
            index = self.node_list.indexOf(self.tree_view)
        else:
            index = self.node_list.indexOf(self.table_view)
        self.node_list.setCurrentIndex(index)

    def _search_node_in_list(self):
        pass

    def _make_new_pov(self, pov_node):
        self.observed_node = pov_node
        new_point = HistoryPoint(self._session, pov_node, grouping=self.chb_grouping.isChecked())
        self.pov_history.append(new_point)
        self.current_history_pos = len(self.pov_history) - 1
        self._toggle_pov_navigation_buttons()
        self._set_dependencies_loading_levels()
        self._reload_dependencies()
    
    def _hide_node(self):
        index = self.table_view.selectionModel().currentIndex()
        history_point = self.pov_history[self.current_history_pos]
        history_point.hide_node(index)
        self._prepare_view()
        self._draw_current_graph()
    
    def _show_node(self):
        index = self.table_view.selectionModel().currentIndex()
        history_point = self.pov_history[self.current_history_pos]
        history_point.show_node(index)
        self._prepare_view()
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
    
    # endregion
    
    # region properties
    @property
    def _active_view(self):
        if self.chb_grouping.isChecked():
            return self.tree_view
        else:
            return self.table_view
    
    # endregion

    # region public methods
    
    def query_node_data(self, node):
        if self._session is None:
            return
        self._make_new_pov(node)
    # endregion
