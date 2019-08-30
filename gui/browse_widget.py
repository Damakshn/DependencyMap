from PySide2 import QtWidgets, QtCore

class BrowseWidget(QtWidgets.QWidget):

    node_selected = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = None
        self.observed_node = None
        self.selected_node = None

    def set_session(self, session):
        self._session = session
    
    def _node_selected(self):
        self.node_selected.emit()

    # ToDo must be signal
    def observed_node_changed(self):
        return self.observed_node
