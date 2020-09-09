import logging
import os
from dpm.connector import Connector
import dpm.models as models
from dpm.linking import analize_links
from sync.scan_db import scan_database
from sync.scan_source import scan_application
from cli import dpm


def create_new_session(config):
    connector = Connector(**config["connector"])
    session = connector.connect_to_dpm()
    return session


def test_scan(config):
    logging.info("Начинаем тестовую синхронизацию")
    connector = Connector(**config["connector"])
    prepare_test_sqlite_db(connector, config)


def prepare_test_sqlite_db(connector, config):
    test_app_config = list(config["applications"].values())[0]
    test_app_name = list(config["applications"].keys())[0]
    test_app_cod = test_app_config.get("cod_application")
    path_to_app = test_app_config["path"]
    test_db_name = config["databases"][0]

    # удаляем временную базу, если она осталась после предыдущего теста
    if os.path.exists(config["connector"]["host_dpm"][10:]):
        os.remove(config["connector"]["host_dpm"][10:])
    session = connector.connect_to_dpm()

    logging.info(f"Соединяемся с базой {test_db_name}")
    try:
        conn = connector.connect_to(test_db_name)
    except Exception:
        logging.critical(f"Не удалось соединиться с БД {test_db_name}; убедитесь, что у вас есть права для этого.")
        exit()

    testdb = models.Database(name=test_db_name)
    session.add(testdb)
    # test_app = models.Application(path=path_to_app, name=test_app_name, last_update=la, default_database=testdb)
    test_app = models.Application(
        path=path_to_app,
        name=test_app_name,
        default_database=testdb,
        cod_application=test_app_cod
    )
    session.add(test_app)
    session.commit()

    logging.info("Начинаем синхронизацию с базой")
    scan_database(testdb, session, conn)
    logging.info("Обработка базы закончена")

    logging.info("Начинаем синхронизацию с АРМом")
    scan_application(test_app, session)
    logging.info("Обработка АРМа закончена")
    session.commit()

    # следующий этап - построение связей
    analize_links(session, conn)
    session.commit()


if __name__ == "__main__":
    dpm()
