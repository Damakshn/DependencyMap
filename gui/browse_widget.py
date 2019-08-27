from PySide2 import QtWidgets

class BrowseWidget(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = None

    def set_session(self, session):
        self._session = session
