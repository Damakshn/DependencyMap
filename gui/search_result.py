from .enums import NodeListColumns
from dpm.graphsworks import NodeStatus
from PySide2 import QtCore

class QtSearchResult:

    """
    Класс для перебора результатов поиска в графе. Позволяет переходить
    от индекса к индексу в табличной и древовидной модели.
    """

    def __init__(self, table_model, tree_model, grouping, result_list):
        self._table_model = table_model
        self._tree_model = tree_model
        self._grouping = grouping
        self._result_list = result_list
        self._table_indexes = []
        self._tree_indexes = []
        self.pos_in_table = 0
        self.pos_in_tree = 0
        self._collect_indexes()
    
    # region properties
    
    @property
    def current_pos(self):
        if self._grouping:
            return self.pos_in_tree
        else:
            return self.pos_in_table

    @property
    def indexes(self):
        if self._grouping:
            return self._tree_indexes
        else:
            return self._table_indexes

    @property
    def index_list_visible(self):
        return [item["index"] for item in self.indexes if item["visible"]]
    
    @property
    def index_list_hidden(self):
        return [item["index"] for item in self.indexes if not item["visible"]]
    
    @property
    def has_hidden(self):
        return (len(self.index_list_hidden) > 0)
    
    # endregion

    # region public methods

    def set_grouping_enabled(self, enabled):
        self._grouping = enabled
        self._collect_indexes()

    def inspect(self):
        """table_buf = []
        for row in range(self._table_model.rowCount()):
            index = self._table_model.index(row, NodeListColumns.ID_COLUMN)
            id = int(self._table_model.data(index))
            if id in self._result_list:
                table_buf.append(index)"""
        print(self._tree_indexes)
    
    def refresh(self):
        self._collect_indexes()
    
    def to_next(self):
        pass

    def to_previous(self):
        pass
    
    # endregion

    # region private methods
    
    def _collect_indexes(self):
        """
        Собирает списки индексов обеих моделей, которые ссылаются на записи,
        содержащие совпадения.
        """
        # каждый индекс пишется в соответствующий список в виде {"index": index, "visible": True/False}
        # собираем индексы табличной модели
        self._table_indexes.clear()
        for row in range(self._table_model.rowCount()):
            id = int(self._table_model.data(self._table_model.index(row, NodeListColumns.ID_COLUMN)))
            if id in self._result_list:
                self._table_indexes.append({
                    "index": self._table_model.index(row, NodeListColumns.ID_COLUMN),
                    "visible": (int(self._table_model.data(self._table_model.index(row, NodeListColumns.STATUS_COLUMN))) == NodeStatus.VISIBLE)
                })
        # индексы древовидной модели
        self._tree_indexes.clear()
        root = self._tree_model.index(0, 0)
        stack = []
        stack.append(root)
        while len(stack) > 0:
            index = stack.pop()
            item = self._tree_model.itemFromIndex(index)
            parent = item.parent()
            parent_index = parent.index() if parent is not None else QtCore.QModelIndex()
            id = self._tree_model.index(row, NodeListColumns.ID_COLUMN, parent_index).data()
            if id is not None:
                id = int(id)
                if id in self._result_list:
                    self._tree_indexes.append({
                        "index": self._tree_model.index(row, NodeListColumns.ID_COLUMN, parent_index),
                        "visible": (int(self._tree_model.data(self._tree_model.index(row, NodeListColumns.STATUS_COLUMN, parent_index))) == NodeStatus.VISIBLE)
                    })
            for row in range(item.rowCount()):
                child_index = self._tree_model.index(row, 0, index)
                stack.append(child_index)

    
    # endregion

    # region dunder methods
    
    def __len__(self):
        return len(self.index_list_visible)
    
    def __str__(self):
        if len(self) == 0:
            if self.has_hidden:
                return f"Найдено {len(self.index_list_hidden)} скрытых совпадений"
            else:
                return "Совпадений не найдено"
        elif self.has_hidden:
            return f"{self.current_pos + 1}-е из {len(self)} совпадений ({len(self.index_list_hidden)} скрыто)"
        else:
            return f"{self.current_pos + 1}-е из {len(self)} совпадений"
    
    def __getitem__(self, key):
        return self.index_list_visible[key]
    
    # endregion
