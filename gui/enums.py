class NodeListColumns:

    structure = [
        {"header": "Тип объекта", "width": 35, "hidden": False},
        {"header": "ID", "width": 100, "hidden": True},
        {"header": "Имя", "width": 400, "hidden": False},
        {"header": "Статус", "width": 100, "hidden": False},
        {"header": "Результат поиска", "width": 100, "hidden": False},
        {"header": "Есть потомки", "width": 100, "hidden": True},
    ]

    ICON_COLUMN = 0
    ID_COLUMN = 1
    NAME_COLUMN = 2
    STATUS_COLUMN = 3
    REVEALED_FOR_SEARCH_COLUMN = 4
    BLIND_COLUMN = 5
