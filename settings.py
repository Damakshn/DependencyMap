import os
import json
import logging

PROJECT_DIR = os.getcwd()
GUI_DIR = os.path.join(PROJECT_DIR, "gui")
PROJECT_NAME = "DPM"

config = json.load(open(os.path.join(PROJECT_DIR, "config.json"), "r", encoding="utf-8"))

logging.basicConfig(filename=config["logfile"], level=logging.DEBUG)

# ToDo add icons mapping for gui

# colors here https://www.rapidtables.com/web/color/html-color-codes.html
# markers here https://matplotlib.org/3.1.0/api/markers_api.html#module-matplotlib.markers
visualization = {
	"nodes": {
		"Database":          {"node_size": 1600, "node_color": "#FFFF00", "node_shape": "*", "linewidths": 3.5, "edgecolors": "#FFD700"},
		"Application":       {"node_size": 1600, "node_color": "#00BFFF", "node_shape": "p", "linewidths": 2.5, "edgecolors": "#00008B"},
		"Form":              {"node_size": 300,  "node_color": "#FF4500", "node_shape": "s", "linewidths": 0.5, "edgecolors": "#000000"},
		"ClientQuery":       {"node_size": 50,   "node_color": "#FF4500", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#00BFFF"},
		"DBTrigger":         {"node_size": 50,   "node_color": "#FF0000", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#DC143C"},
		"DBStoredProcedure": {"node_size": 50,   "node_color": "#00BFFF", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#0000FF"},
		"DBView":            {"node_size": 50,   "node_color": "#32CD32", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#000000"},
		"DBTableFunction":   {"node_size": 50,   "node_color": "#A0522D", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#000000"},
		"DBScalarFunction":  {"node_size": 50,   "node_color": "#FF00FF", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#000000"},
		"DBTable":           {"node_size": 100,  "node_color": "#DCDCDC", "node_shape": "s", "linewidths": 0.5, "edgecolors": "#000000"},
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