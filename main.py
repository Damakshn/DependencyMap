import logging
import os
import json
import datetime
import calendar
from dpm.connector import Connector
import dpm.models as models
from sync.db_sync import sync_database
from sync.source_sync import sync_separate_app
import matplotlib.pyplot as plt
import networkx as nx


path_to_config = "config.json"

def set_logger(logfile):
	logging.basicConfig(filename=logfile, level=logging.DEBUG)

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

def prepare_test_sqlite_db(connector, config):
	path_to_app = config["testApp"]
	app_name = config["testAppName"]
	test_db_name = config["testdb"]
	# удаляем временную базу, если она осталась после предыдущего теста
	if os.path.exists(config["connector"]["host_dpm"][10:]):
		os.remove(config["connector"]["host_dpm"][10:])
	session = connector.connect_to_dpm()
	logging.info(f"Соединяемся с базой {config['testdb']}")
	try:
		conn = connector.connect_to(config["testdb"])
	except Exception as e:
		logging.critical(f"Не удалось соединиться с БД {config['testdb']}; убедитесь, что у вас есть права для этого.")
		exit()
	# создаём тестовый АРМ, чтобы синхронизировать его
	d = datetime.datetime.now()
	# создаём искусственную дату обновления, чтобы синхронизация сработала
	la = datetime.datetime.fromtimestamp(
		calendar.timegm((datetime.date.today() - datetime.timedelta(days=30)).timetuple())
	)
	test_app = models.Application(
		path=path_to_app,
		name=app_name,
		last_update=la
	)
	session.add(test_app)
	# создаём в базе ДПМ запись о тестовой базе, чтобы было что синхронизировать
	testdb = models.Database(
		name=test_db_name,
		last_revision=la,
		last_update=la
	)
	session.add(testdb)
	session.flush()
	logging.info(f"Начинаем синхронизацию с АРМом")
	sync_separate_app(test_app, session)
	logging.info(f"Обработка АРМа закончена")
	logging.info(f"Начинаем синхронизацию с базой")
	sync_database(testdb, session, conn)
	logging.info(f"Обработка базы закончена")
	session.commit()

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
