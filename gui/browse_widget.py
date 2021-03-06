from PySide2 import QtWidgets, QtCore

class BrowseWidget(QtWidgets.QWidget):

    node_selected = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._storage = None
        self.observed_node = None
        self.selected_node = None

    def set_storage(self, storage):
        self._storage = storage
    
    def _set_selected_node(self, node):
        self.selected_node = node
        self.node_selected.emit()

    def clear(self):
        self.observed_node = None
        self._set_selected_node(None)
