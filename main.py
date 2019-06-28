import logging
import os
import json
import datetime
import calendar
from dpm.connector import Connector
import dpm.models as models
from dpm.linking import analize_links
from sync.scan_db import scan_database
from sync.scan_source import scan_application
import matplotlib.pyplot as plt
import networkx as nx


def viz_test(app):
	G = nx.DiGraph()
	G.add_node(app.name, label=app.name, node_class="Application")
	for form_path in app.forms:
		form_name = app.forms[form_path].alias
		G.add_node(form_name, label=form_name, node_class="Form")
		G.add_edge(app.name, form_name)
		for component in app.forms[form_path].components:
			G.add_node(component, label=component, node_class="Component")
			G.add_edge(form_name, component)
			for link in app.forms[form_path].components[component].edges_out:
				G.add_node(link.to_node.name, label=link.to_node.name, node_class="DBObject")
				G.add_edge(component, link.to_node.name)
	pos = nx.spring_layout(G)
	nx.draw_networkx_nodes(G, pos, [n for n in G.node if G.node[n]["node_class"]=="Application"], node_size=500, node_color='red')
	nx.draw_networkx_nodes(G, pos, [n for n in G.node if G.node[n]["node_class"]=="Form"], node_size=200, node_color='blue', node_shape="s")
	nx.draw_networkx_nodes(G, pos, [n for n in G.node if G.node[n]["node_class"]=="Component"], node_size=100, node_color='green', node_shape="D")
	nx.draw_networkx_nodes(G, pos, [n for n in G.node if G.node[n]["node_class"]=="DBObject"], node_size=50, node_color='red', node_shape="p")
	
	nx.draw_networkx_edges(G, pos)
	nx.draw_networkx_labels(G, pos)
	
	plt.axis('off')
	plt.show()

def draw_table_graph(tbl, select=True, insert=True, update=True, delete=True):
	G = nx.DiGraph()
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
	nx.draw_networkx_edges(G, pos, [e for e in G.edges() if G.edges()[e]["edge_class"]=="select"], edge_color='black')
	nx.draw_networkx_edges(G, pos, [e for e in G.edges() if G.edges()[e]["edge_class"]=="insert"], edge_color='blue')
	nx.draw_networkx_edges(G, pos, [e for e in G.edges() if G.edges()[e]["edge_class"]=="update"], edge_color='cyan')
	nx.draw_networkx_edges(G, pos, [e for e in G.edges() if G.edges()[e]["edge_class"]=="delete"], edge_color='red')

	nx.draw_networkx_nodes(G, pos)
	nx.draw_networkx_labels(G, pos)
	plt.axis('off')
	plt.show()
	


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

path_to_config = "config.json"

def set_logger(logfile):
	logging.basicConfig(filename=logfile, level=logging.DEBUG)


def prepare_test_sqlite_db(connector, config):
	test_app_config = list(config["applications"].values())[0]
	test_app_name = list(config["applications"].keys())[0]
	path_to_app = test_app_config["path"]
	test_db_name = config["databases"][0]
	
	# удаляем временную базу, если она осталась после предыдущего теста
	#if os.path.exists(config["connector"]["host_dpm"][10:]):
	#	os.remove(config["connector"]["host_dpm"][10:])
	session = connector.connect_to_dpm()
	logging.info(f"Соединяемся с базой {config['testdb']}")
	try:
		conn = connector.connect_to(config["testdb"])
	except Exception as e:
		logging.critical(f"Не удалось соединиться с БД {config['testdb']}; убедитесь, что у вас есть права для этого.")
		exit()
	"""
	# создаём тестовый АРМ, чтобы синхронизировать его
	d = datetime.datetime.now()
	# создаём искусственную дату обновления, чтобы синхронизация сработала
	la = datetime.datetime.fromtimestamp(
		calendar.timegm((datetime.date.today() - datetime.timedelta(days=30)).timetuple())
	)
	# создаём в базе ДПМ запись о тестовой базе, чтобы было что синхронизировать
	testdb = models.Database(name=test_db_name, last_revision=la, last_update=la)
	session.add(testdb)
	test_app = models.Application(path=path_to_app, name=test_app_name, last_update=la, default_database=testdb)
	session.add(test_app)
	session.commit()
	
	logging.info(f"Начинаем синхронизацию с базой")
	scan_database(testdb, session, conn)
	logging.info(f"Обработка базы закончена")

	logging.info(f"Начинаем синхронизацию с АРМом")
	scan_application(test_app, session)
	logging.info(f"Обработка АРМа закончена")
	session.commit()
	"""
	# следующий этап - построение связей
	#analize_links(session, conn)

	#viz_test(session.query(models.Application).filter_by(name=test_app_name).one())
	
	draw_table_graph(
		session.query(models.DBTable).filter_by(name="bs_Listener").one(),
		select=True,
		insert=True,
		update=True,
		delete=True
	)

def main():
	config = read_config()
	set_logger(config["logfile"])
	logging.info(f"Начинаем тестовую синхронизацию")
	connector = Connector(**config["connector"])
	prepare_test_sqlite_db(connector, config)

def read_config():
	return json.load(open(path_to_config, "r", encoding="utf-8"))

if __name__ == "__main__":
	main()
