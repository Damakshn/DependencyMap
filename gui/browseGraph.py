from PySide2 import QtWidgets, QtGui


icons_for_nodes = {}

class BrowseGraphWidget(QtWidgets.QWidget):
    """
    Большой виджет, отвечающий за работу с графом зависимостей.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_history_pos = None
        self.pov_history = []

        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 1)

        self.setLayout(grid)
        self._init_draw_area()
        self._init_control_panel()

    def _init_draw_area(self):
        # ToDo пока используем болванку
        self.draw_area = QtWidgets.QWidget()
        self.draw_area.setStyleSheet("background-color: #FFFFE0;")
        self.layout().addWidget(self.draw_area, 0, 0)
        # 

    def _init_control_panel(self):
        # Панель управления отображением графа и содержащая список объектов.
        self.control_panel = QtWidgets.QWidget()
        self.control_panel.setLayout(QtWidgets.QVBoxLayout())
        # widgets for control_panel
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
        self.pov_icon.setPixmap(QtGui.QPixmap("assets/package.png"))
        grid.addWidget(self.pov_icon, 0, 0)
        # имя точки отсчёта
        self.pov_label = QtWidgets.QLabel()
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
        """
        ToDo
            signals:
                pov_first/pov_back/pov_forward/pov_last.clecked.connect(...)
        """
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
        spb_up = QtWidgets.QSpinBox()
        spb_down = QtWidgets.QSpinBox()

        spb_up.setValue(0)
        spb_down.setValue(3)

        chb_up = QtWidgets.QCheckBox("До конца")
        chb_down = QtWidgets.QCheckBox("До конца")

        bt_load = QtWidgets.QPushButton("Загрузить")

        grid.addWidget(lb_up, 0, 0)
        grid.addWidget(spb_up, 0, 1)
        grid.addWidget(chb_up, 0, 2)

        grid.addWidget(lb_down, 1, 0)
        grid.addWidget(spb_down, 1, 1)
        grid.addWidget(chb_down, 1, 2)
        grid.addWidget(bt_load, 0, 3, 2, 1)
        panel = QtWidgets.QWidget()
        panel.setLayout(grid)
        panel.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.control_panel.layout().addWidget(panel)

    def _init_list_control_panel(self):
        # панель управления списком объектов (поиск и группировка)
        lb_search = QtWidgets.QLabel("Поиск:")
        le_search = QtWidgets.QLineEdit()
        chb_grouping = QtWidgets.QCheckBox("Группировка")
        """
        ToDo
            signals:
                chb_grouping.stateChanged.connect(...) - переключение группировки
                le_search.returnPressed.connect(...) - включение поиска
        """
        grid = QtWidgets.QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 5)

        grid.addWidget(lb_search, 0, 0)
        grid.addWidget(le_search, 0, 1)
        grid.addWidget(chb_grouping, 1, 0, 1, 2)

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
        node_list = QtWidgets.QWidget()
        node_list.setStyleSheet("background-color: #FFFFE0;")
        node_list.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)
        self.control_panel.layout().addWidget(node_list)

    def load_data(self, first_pov):
        """
        Инициализирует данные виджета.
        """
        pass
    
    def _reload_dependencies(self):
        pass
    
    def _draw_current_graph(self):
        pass

    def _read_graph_from_history(self):
        """
        Читает граф из текущей позиции в истории, заполняет значения виджетов значениями
        из атрибутов графа и выводит граф в области для отображения.
        """
        pass

    def _change_pov(self, button):
        """
        движение по истории точек отсчёта
        в зависимости от того, какая кнопка была нажата, двигается вперёд, назада, в начало или в конец
        если достигнуто начало истории просмотров, то кнопки "в начало" и "назад" выключаются, если 
        достигнут конец, то выключаются кнопки "Вперёд" и "в конец".
        """
        pass


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
