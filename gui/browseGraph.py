import os
from PySide2 import QtWidgets, QtGui, QtCore
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from .browse_widget import BrowseWidget
import settings
from dpm.graphsworks import DpmGraph, NodeStatus
from .collection import IconCollection
from .historyPoint import HistoryPoint, NodeListColumns


class BrowseGraphWidget(BrowseWidget):
    """
    Большой виджет, отвечающий за работу с графом зависимостей.
    """
    # region ToDO
    # большие фичи интерфейса:
    #   ToDo поиск
    #       ToDo обработка скрытых нод при поиске: выводить в описании результата, что есть скрытые ноды, кнопка "Показать", показ скрытых результатов
    #       ToDo фокус на объекте в таблице\дереве при поиске
    #       ToDo правильный перебор результатов, если они были показаны через контекстное меню в списке, проблема с нулевым индексом
    #       ToDo перенос позиции в результате в класс SearchResult? (чтобы правильно показывать номер позиции в надписи на панели поиска)
    #   ToDo невозможность вызвать контекстное меню на точке отсчета в списке
    #   ToDo спрятанная вершина со спрятанным родителем тоже должна исчезнуть
    # структура кода:
    # Область отображения:
    #   ToDo узнать, можно ли добавить зум и другие плюшки
    #   ToDo надо увеличить размер области рисования, чтобы она занимала всё окно
    # дополнения
    #   ToDo выводить количество объектов в списке в виде Объектов: *, отображается: *
    #   ToDo всплывающие подсказки для кнопок
    # на будущее
    #   ToDo экспорт графа в другие форматы
    # endregion

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_history_pos = 0
        self.pov_history = []
        self.last_search_request = ""
        self.search_result = None
        self.current_result_pos = 0
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
        self.node_action_set_pov.triggered.connect(self._switch_to_new_pov)

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
        self.le_search.returnPressed.connect(self._handle_search)
        self.chb_grouping = QtWidgets.QCheckBox("Группировка")
        self.chb_grouping.stateChanged.connect(self._toggle_grouping)
        self.bt_next_result = QtWidgets.QPushButton()
        self.bt_next_result.setIcon(IconCollection.pixmaps["down"])
        self.bt_next_result.clicked.connect(self._move_to_next_search_result)
        self.bt_prev_result = QtWidgets.QPushButton()
        self.bt_prev_result.clicked.connect(self._move_to_previous_search_result)
        self.bt_prev_result.setIcon(IconCollection.pixmaps["up"])
        self.search_result_text = QtWidgets.QLabel("")
        self.bt_show_hidden_results = QtWidgets.QPushButton("Показать скрытое")
        self.bt_show_hidden_results.setVisible(False)

        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(4, 5)
        grid.setColumnStretch(5, 2)

        grid.addWidget(lb_search, 0, 0)
        grid.addWidget(self.le_search, 0, 1)
        grid.addWidget(self.bt_next_result, 0, 2)
        grid.addWidget(self.bt_prev_result, 0, 3)
        grid.addWidget(self.search_result_text, 0, 4)
        grid.addWidget(self.bt_show_hidden_results, 0, 5)
        
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
        self.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_node_context_menu)

        self.table_view = QtWidgets.QTableView()
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_node_context_menu)
        self.table_view.horizontalHeader().hide()
        self.table_view.verticalHeader().hide()

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
        chosen_index = self._active_view.selectionModel().selectedRows()[0]
        model = self._active_view.model()
        status = int(model.data(model.index(chosen_index.row(), NodeListColumns.STATUS_COLUMN, chosen_index.parent())))
        if status == NodeStatus.ROLLED_UP:
            self.node_context_menu.addAction(self.node_action_show)
        else:
            self.node_context_menu.addAction(self.node_action_hide)
        
        self.node_context_menu.exec_(self.table_view.viewport().mapToGlobal(position))
    
    def _process_row_selection(self):
        chosen_index = self._active_view.selectionModel().currentIndex()
        model = self._active_view.model()
        node_id = model.data(model.index(chosen_index.row(), NodeListColumns.ID_COLUMN, chosen_index.parent()))
        # на выбор стрелки в дереве не реагируем
        if node_id is None:
            self._set_selected_node(None)
        else:
            node_id = int(node_id)
            self._set_selected_node(self._storage.get_node_by_id(node_id))

    def _set_table_model(self, model):
        """
        Устанавливает табличную модель для виджета со списком вершин графа.
        """
        self.table_view.setModel(model)
        for column in range(len(NodeListColumns.structure)):
            self.table_view.setColumnWidth(column, NodeListColumns.structure[column]["width"])
            self.table_view.setColumnHidden(column, NodeListColumns.structure[column]["hidden"])

    def _set_tree_model(self, model):
        """
        Устанавливает древовидную модель для виджета со списком вершин графа.
        """
        self.tree_view.setModel(model)
        #for column in range(len(NodeListColumns.structure)):
            #self.tree_view.setColumnHidden(column, NodeListColumns.structure[column]["hidden"])
    
    def _prepare_view(self):
        # прячем в списке те объекты, которые были скрыты автоматически
        table_model = self.table_view.model()
        for row in range(table_model.rowCount()):
            self.table_view.setRowHidden(
                row,
                int(table_model.index(row, NodeListColumns.STATUS_COLUMN).data()) == NodeStatus.AUTO_HIDDEN
            )
        
        # деревянная модель
        tree_model = self.tree_view.model()
        stack = []
        parent = QtCore.QModelIndex()
        stack.append(parent)
        while len(stack) > 0:
            parent = stack.pop()
            row = parent.row()
            # читаем статус вершины, чтобы понять, надо ли прятать её потомков
            status = tree_model.index(row, NodeListColumns.STATUS_COLUMN, parent.parent()).data()
            status = int(status) if status is not None else None
            if tree_model.hasChildren(parent) == False:
                continue
            if status in (NodeStatus.ROLLED_UP, NodeStatus.AUTO_HIDDEN):
                # если вершина спрятана, то прячем её потомков
                for child_row in range(tree_model.rowCount(parent)):
                    self.tree_view.setRowHidden(child_row, parent, True)
            else:
                for child_row in range(tree_model.rowCount(parent)):
                    self.tree_view.setRowHidden(child_row, parent, False)
                # если нода является видимой в списке, то обрабатываем её потомков
                for child_row in range(tree_model.rowCount(parent=parent)):
                    stack.append(tree_model.index(child_row, 0, parent))
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
        self.pov_history[self.current_history_pos].set_grouping_enagled(self.chb_grouping.isChecked())

    def _handle_search(self):
        search_term = self.le_search.text().strip()
        if search_term == "":
            QtWidgets.QMessageBox.about(self, "Ошибка", "Введите критерий поиска")
            return
        if search_term != self.last_search_request:
            self.last_search_request = search_term
            self.le_search.setText(self.last_search_request)
            search_result = self.pov_history[self.current_history_pos].search_node_by_label(self.last_search_request)
            self.search_result = search_result
            self.current_result_pos = 0
            self._update_search_result()
        self._focus_on_current_search_result()
    
    def _focus_on_current_search_result(self):
        if self.search_result is None or len(self.search_result) == 0:
            return
        node = self.search_result.get_current_match()
        next_node_id = node["id"]
        QtWidgets.QMessageBox.about(self, "Результат поиска", f"id - {next_node_id}, {self.search_result.current_pos + 1} of {len(self.search_result)}")

    def _move_to_next_search_result(self):
        if self.search_result is None or len(self.search_result) == 0:
            return
        self.search_result.to_next()
        self._focus_on_current_search_result()

    
    def _move_to_previous_search_result(self):
        if self.search_result is None or len(self.search_result) == 0:
            return
        self.search_result.to_previous()
        self._focus_on_current_search_result()
    
    def _update_search_result(self):
        if self.search_result is not None:
            self.search_result_text.setText(str(self.search_result))
            self.bt_show_hidden_results.setVisible(self.search_result.has_hidden)

    def _bind_selection_signals(self):
        self.table_view.selectionModel().selectionChanged.connect(self._process_row_selection)
        self.tree_view.selectionModel().selectionChanged.connect(self._process_row_selection)
    
    def _switch_to_new_pov(self):
        self._make_new_pov(self.selected_node)
        

    def _make_new_pov(self, pov_node):
        self.observed_node = pov_node
        new_point = HistoryPoint(self._storage, pov_node, grouping=self.chb_grouping.isChecked())
        self.pov_history.append(new_point)
        self.current_history_pos = len(self.pov_history) - 1
        self._toggle_pov_navigation_buttons()
        self._set_dependencies_loading_levels()
        self._reload_dependencies()
        self._bind_selection_signals()
    
    def _hide_node(self):
        index = self._active_view.selectionModel().currentIndex()
        history_point = self.pov_history[self.current_history_pos]
        history_point.hide_node(index)
        self._prepare_view()
        self._draw_current_graph()
        self._update_search_result()
    
    def _show_node(self):
        index = self._active_view.selectionModel().currentIndex()
        history_point = self.pov_history[self.current_history_pos]
        history_point.show_node(index)
        self._prepare_view()
        self._draw_current_graph()
        self._update_search_result()

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
        if self._storage is None:
            return
        self._make_new_pov(node)
    # endregion
