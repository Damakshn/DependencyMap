def get_config():
    """
    Возвращает словарь с настройками отрисовки вершин и рёбер различных типов.
    """
    # ToDo вынести в конфиг
    # ToDo добавить настройки рисования связи между таблицей и её триггером
    # colors here https://www.rapidtables.com/web/color/html-color-codes.html
    # markers here https://matplotlib.org/3.1.0/api/markers_api.html#module-matplotlib.markers
    return {
        "nodes": {
            "Database":          {"node_size": 1600, "node_color": "#FFFF00", "rgb":{"r": 255, "g": 255, "b": 0}, "node_shape": "*", "linewidths": 3.5, "edgecolors": "#FFD700"},
            "Application":       {"node_size": 1600, "node_color": "#00BFFF", "rgb":{"r": 0, "g": 191, "b": 255}, "node_shape": "p", "linewidths": 2.5, "edgecolors": "#00008B"},
            "Form":              {"node_size": 300,  "node_color": "#FF4500", "rgb":{"r": 255, "g": 69, "b": 0}, "node_shape": "s", "linewidths": 0.5, "edgecolors": "#000000"},
            "ClientQuery":       {"node_size": 50,   "node_color": "#FF4500", "rgb":{"r": 255, "g": 69, "b": 0}, "node_shape": "d", "linewidths": 0.5, "edgecolors": "#00BFFF"},
            "DBTrigger":         {"node_size": 50,   "node_color": "#FF0000", "rgb":{"r": 255, "g": 0, "b": 0}, "node_shape": "d", "linewidths": 0.5, "edgecolors": "#DC143C"},
            "DBStoredProcedure": {"node_size": 50,   "node_color": "#00BFFF", "rgb":{"r": 0, "g": 191, "b": 255}, "node_shape": "d", "linewidths": 0.5, "edgecolors": "#0000FF"},
            "DBView":            {"node_size": 50,   "node_color": "#32CD32", "rgb":{"r": 160, "g": 82, "b": 45}, "node_shape": "d", "linewidths": 0.5, "edgecolors": "#000000"},
            "DBTableFunction":   {"node_size": 50,   "node_color": "#A0522D", "rgb":{"r": 255, "g": 255, "b": 0}, "node_shape": "d", "linewidths": 0.5, "edgecolors": "#000000"},
            "DBScalarFunction":  {"node_size": 50,   "node_color": "#FF00FF", "rgb":{"r": 255, "g": 0, "b": 255}, "node_shape": "d", "linewidths": 0.5, "edgecolors": "#000000"},
            "DBTable":           {"node_size": 100,  "node_color": "#DCDCDC", "rgb":{"r": 220, "g": 220, "b": 220}, "node_shape": "s", "linewidths": 0.5, "edgecolors": "#000000"},
        },
        "edges": {
            "select":   {"width": 0.3, "edge_color": "#32CD32", "style": "solid", "alpha": 0.7, "arrows": True, "label": None},
            "insert":   {"width": 0.3, "edge_color": "#FF4500", "style": "solid", "alpha": 0.7, "arrows": True, "label": None},
            "update":   {"width": 0.3, "edge_color": "#00FFFF", "style": "solid", "alpha": 0.7, "arrows": True, "label": None},
            "delete":   {"width": 0.3, "edge_color": "#DC143C", "style": "solid", "alpha": 0.7, "arrows": True, "label": None},
            "exec":     {"width": 0.3, "edge_color": "#0000FF", "style": "solid", "alpha": 0.7, "arrows": True, "label": None},
            "drop":     {"width": 1.5, "edge_color": "#FF0000", "style": "solid", "alpha": 1.0, "arrows": True, "label": None},
            "truncate": {"width": 1.0, "edge_color": "#9400D3", "style": "solid", "alpha": 1.0, "arrows": True, "label": None},
            "contain":  {"width": 0.3, "edge_color": "#000000", "style": "solid", "alpha": 0.7, "arrows": True, "label": None},
            "calc":     {"width": 0.3, "edge_color": "#9400D3", "style": "solid", "alpha": 0.7, "arrows": True, "label": None},
            "trigger":  {"width": 0.3, "edge_color": "#FFD700", "style": "solid", "alpha": 0.7, "arrows": True, "label": None},
        }
    }
