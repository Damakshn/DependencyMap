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
import dpm.visualization as viz
import dpm.graphsworks as gw


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
	"""
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
	#session.commit()
		
	viz.draw_graph(gw.build_graph_in_depth(session.query(models.Database).filter_by(name=test_db_name).one()))
	

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
