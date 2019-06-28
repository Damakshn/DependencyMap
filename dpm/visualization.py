import matplotlib.pyplot as plt
import networkx as nx

def draw_graph_for(parent_node):
	G = nx.Graph()
	print("Запрашиваем ссылки")
	child_links = parent_node.links_out
	print("Заполняем связи графа")
	for link in child_links:
		G.add_edge(parent_node.name, link.to_node.name)
	print("Расставляем объекты")
	pos = nx.spring_layout(G)  # positions for all nodes
	print("Рисуем ноды")
	nx.draw_networkx_nodes(G, pos, node_size=20)
	print("Рисуем связи")
	nx.draw_networkx_edges(G, pos)
	print("Рисуем подписи")
	nx.draw_networkx_labels(G, pos, font_size=5, font_family='sans-serif')
	print("Выводим результат")
	plt.show()

def draw_tables_for(database):
	G = nx.Graph()
	for table in database.tables:
		G.add_edge(database.name, table.name)
	print("Расставляем объекты")
	pos = nx.spring_layout(G)  # positions for all nodes
	print("Рисуем ноды")
	nx.draw_networkx_nodes(G, pos, node_size=20)
	print("Рисуем связи")
	nx.draw_networkx_edges(G, pos)
	print("Рисуем подписи")
	nx.draw_networkx_labels(G, pos, font_size=5, font_family='sans-serif')
	print("Выводим результат")
	plt.show()
