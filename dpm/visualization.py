import matplotlib.pyplot as plt
import networkx as nx
import dpm.graphsworks as gw


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
			"Database":          {"node_size": 1600, "node_color": "#FFFF00", "node_shape": "*", "linewidths": 3.5, "edgecolors": "#FFD700"}, # золотая звезда
			"Application":       {"node_size": 1600, "node_color": "#00BFFF", "node_shape": "p", "linewidths": 2.5, "edgecolors": "#00008B"}, # синий пятиугольник 
			"Form":              {"node_size": 300,  "node_color": "#FF4500", "node_shape": "s", "linewidths": 0.5, "edgecolors": "#000000"}, # оранжевый квадрат
			"ClientQuery":       {"node_size": 50,   "node_color": "#FF4500", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#00BFFF"}, # оранжевый ромб
			"DBTrigger":         {"node_size": 50,   "node_color": "#FF0000", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#DC143C"}, # красный ромб
			"DBStoredProcedure": {"node_size": 50,   "node_color": "#00BFFF", "node_shape": "d", "linewidths": 0.5, "edgecolors": "#0000FF"}, # гобубой ромб
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


def draw_graph(G):
	
	config = get_config()
	
	pos = nx.spring_layout(G)
	
	for class_name in config["nodes"]:
		nx.draw_networkx_nodes(G, pos, [n for n in G.node if G.node[n]["node_class"]==class_name], **config["nodes"][class_name])
	
	for operation in config["edges"]:
		nx.draw_networkx_edges(G, pos, [e for e in G.edges if G.adj[e[0]][e[1]][0].get(operation)==True], **config["edges"][operation])
	
	nx.draw_networkx_labels(G, pos, {n:G.node[n]["label"] for n in G.node}, font_size=6)

	plt.axis('off')
	plt.show()


def draw_dependency_between():
	# путь от одного объекта к другому
	"""
	P = nx.Graph()
	P.add_node(form.name)
	for path in nx.all_shortest_paths(G, form.name, "Student"):
		prev = form.name
		for node_index in range(1, len(path)):
			P.add_node(path[node_index])
			P.add_edge(prev, path[node_index], **G.adj[prev][path[node_index]])
			prev = path[node_index]
	pos = nx.random_layout(P)
	nx.draw_networkx(P, pos)
	plt.axis('off')
	plt.show()
	"""
	pass