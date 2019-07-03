import matplotlib.pyplot as plt
import networkx as nx
import dpm.graphsworks as gw


def get_config():
	# colors here https://www.rapidtables.com/web/color/html-color-codes.html
	# markers here https://matplotlib.org/3.1.0/api/markers_api.html#module-matplotlib.markers
	return {
		"Database":          {"node_size": 500, "node_color": "#FFD700", "node_shape": "*", "linewidths": 0.5, "edgecolors": "black"},
		"Application":       {"node_size": 300, "node_color": "#696969", "node_shape": "p", "linewidths": 0.5, "edgecolors": "black"},
		"Form":              {"node_size": 100, "node_color": "#FF4500", "node_shape": "s", "linewidths": 0.5, "edgecolors": "black"},
		"ClientQuery":       {"node_size": 50,  "node_color": "#00FFFF", "node_shape": "d", "linewidths": 0.5, "edgecolors": "black"},
		"DBTrigger":         {"node_size": 70,  "node_color": "#FF0000", "node_shape": "d", "linewidths": 0.5, "edgecolors": "black"},
		"DBStoredProcedure": {"node_size": 50,  "node_color": "#4B0082", "node_shape": "d", "linewidths": 0.5, "edgecolors": "black"},
		"DBView":            {"node_size": 50,  "node_color": "#32CD32", "node_shape": "d", "linewidths": 0.5, "edgecolors": "black"},
		"DBTableFunction":   {"node_size": 50,  "node_color": "#A0522D", "node_shape": "d", "linewidths": 0.5, "edgecolors": "black"},
		"DBScalarFunction":  {"node_size": 50,  "node_color": "#FF00FF", "node_shape": "d", "linewidths": 0.5, "edgecolors": "black"},
		"DBTable":           {"node_size": 100, "node_color": "#000000", "node_shape": "s", "linewidths": 0.5, "edgecolors": "black"},
	}



def draw_graph(G):
	config = get_config()
	pos = nx.spring_layout(G)
	
	for class_name in config:
		nx.draw_networkx_nodes(G, pos, [n for n in G.node if G.node[n]["node_class"]==class_name], **config[class_name])

	nx.draw_networkx_edges(G, pos, [e for e in G.edges()], width=0.3, alpha=0.4)
	nx.draw_networkx_labels(G, pos, {n:G.node[n]["label"] for n in G.node}, font_size=8)

	plt.axis('off')
	plt.show()

def draw_table_graph(tbl, select=True, insert=True, update=True, delete=True):
	G = nx.Graph()
	G.add_node(tbl.name, label=tbl.name, node_class="DBTable")
	if select:
		for e in [e for e in tbl.edges_in if e.select]:
			G.add_node(e.from_node.name, label=e.from_node.name)
			G.add_edge(e.from_node.name, tbl.name, edge_class="select")
	if insert:
		for e in [e for e in tbl.edges_in if e.insert]:
			G.add_node(e.from_node.name, label=e.from_node.name)
			G.add_edge(e.from_node.name, tbl.name, edge_class="insert")
	if update:
		for e in [e for e in tbl.edges_in if e.update]:
			G.add_node(e.from_node.name, label=e.from_node.name)
			G.add_edge(e.from_node.name, tbl.name, edge_class="update")
	if delete:
		for e in [e for e in tbl.edges_in if e.delete]:
			G.add_node(e.from_node.name, label=e.from_node.name)
			G.add_edge(e.from_node.name, tbl.name, edge_class="delete")
	
	pos = nx.spring_layout(G)

	nx.draw_networkx_edges(G, pos, [e for e in G.edges() if G.edges()[e]["edge_class"]=="select"], edge_color='black', width=1, alpha=0.5)
	nx.draw_networkx_edges(G, pos, [e for e in G.edges() if G.edges()[e]["edge_class"]=="insert"], edge_color='blue',  width=1, alpha=0.5)
	nx.draw_networkx_edges(G, pos, [e for e in G.edges() if G.edges()[e]["edge_class"]=="update"], edge_color='cyan',  width=1, alpha=0.5)
	nx.draw_networkx_edges(G, pos, [e for e in G.edges() if G.edges()[e]["edge_class"]=="delete"], edge_color='red',   width=1, alpha=0.5)
	
	nx.draw_networkx_nodes(G, pos, [n for n in G.node if n != tbl.name], node_size=50, node_color='green')

	nx.draw_networkx_nodes(G, pos, [tbl.name], node_color='red')
	nx.draw_networkx_labels(G, pos)
	plt.axis('off')
	plt.show()
	
def draw_form_graph(form):
	G = nx.Graph()
	G.add_node(form.name, label=form.name, node_class="Form")
	for component_name in form.components:
		G.add_node(component_name, lable=component_name, node_class="Component")
		G.add_edge(form.name, component_name, edge_class="from_form_to_component")
		for e in form.components[component_name].edges_out:
			G.add_node(e.to_node.name, label=e.to_node.name, node_class="DBObject")
			G.add_edge(component_name, e.to_node.name, edge_class="from_component_to_dbobject", tmplt={'raz':1, 'dva': 2})
	
	pos = nx.spring_layout(G)
	nx.draw_networkx_edges(G, pos, G.edges(), edge_color='black', width=0.3, alpha=0.5)
	nx.draw_networkx_nodes(G, pos, [form.name], node_size=200, node_color='red', node_shape="s")
	nx.draw_networkx_nodes(G, pos, [n for n in G.node if G.node[n]["node_class"]=="Component"], node_size=50, node_color='purple')
	nx.draw_networkx_nodes(G, pos, [n for n in G.node if G.node[n]["node_class"]=="DBObject"], node_size=50, node_color='black')
	nx.draw_networkx_labels(G, pos)
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