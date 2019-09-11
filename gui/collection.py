from PySide2 import QtGui
import os
import settings


class IconCollection:
    """
    Разделяемая коллекция иконок
    """
    icons = {}
    pixmaps = {}

    @classmethod
    def initialize(cls):
        if len(IconCollection.icons) > 0 or len(IconCollection.pixmaps) > 0:
            return
        IconCollection.icons = {
            "DBTable": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/table.png")),
            "DBView": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/view.png")),
            "DBStoredProcedure": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/procedure.png")),
            "Application": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/application.png")),
            "Form": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/form.png")),
            "ClientQuery": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/component.png")),
            "DBTrigger": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/trigger.png")),
            "DBScalarFunction": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/function.png")),
            "DBTableFunction": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/table_function.png")),
            "GenericNode": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/generic.png")),
            "node_in_list": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/table32.png")),
            "program": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/system48.jpg")),
            "browse_system": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/system48.png")),
            "browse_object":  QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/list48.png")),
            "browse_graph":  QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/network48.png")),
            "new_pov": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/new_pov.png")),
            "invisible": QtGui.QIcon(os.path.join(settings.GUI_DIR, "assets/invisible.png")),
        }

        IconCollection.pixmaps = {
            "pov_node": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/package.jpg")),
            "begin": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/begin32.png")),
            "back": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/back32.png")),
            "forward": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/forward32.png")),
            "end": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/end32.png")),

            "DBTable": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/table.png")),
            "DBView": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/view.png")),
            "DBStoredProcedure": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/procedure.png")),
            "Application": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/application.png")),
            "Form": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/form.png")),
            "ClientQuery": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/component.png")),
            "DBTrigger": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/trigger.png")),
            "DBScalarFunction": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/function.png")),
            "DBTableFunction": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/table_function.png")),
            "GenericNode": QtGui.QPixmap(os.path.join(settings.GUI_DIR, "assets/generic.png")),
        }
    
    # ToDo use decorator?
    @classmethod
    def get_icon_for_node_class(cls, node_class):
        if len(IconCollection.icons) == 0 or len(IconCollection.pixmaps) == 0:
            raise Exception("Коллекция иконок не инициализирована!")
        return IconCollection.icons.get(node_class, IconCollection.icons["GenericNode"])

    
    @classmethod
    def get_pixmap_for_node_class(cls, node_class):
        if len(IconCollection.icons) == 0 or len(IconCollection.pixmaps) == 0:
            raise Exception("Коллекция иконок не инициализирована!")
        return IconCollection.pixmaps.get(node_class, IconCollection.pixmaps["GenericNode"])
        



