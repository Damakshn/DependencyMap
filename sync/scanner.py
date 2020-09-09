import logging
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from dpm.connector import Connector
from dpm import models


logger = logging.getLogger(__name__)


class DpmScanner:

    def __init__(self, connection_data):
        self._connector = Connector(**connection_data)
        self._session = self._connector.connect_to_dpm()
        self._applications = []
        self._databases = []

    def load_applications(self, data):
        for application_name in data:
            try:
                application = self._session.query(models.Application).filter_by(name=application_name).one()
            except NoResultFound:
                application = models.Application(
                    path=data[application_name]["path"],
                    name=application_name,
                    default_database=data[application_name]["default_database"],
                    cod_application=data[application_name].get("cod_application")
                )
            except MultipleResultsFound:
                logger.error(f"Найдены 2 или более приложения {application_name}, сканирование проводиться не будет")
            self._applications.append(application)

    def load_databases(self, data):
        for database_name in data:
            try:
                database = self._session.query(models.Database).filter_by(name=database_name).one()
            except NoResultFound:
                database = models.Database(
                    name=database_name
                )
            except MultipleResultsFound:
                logger.error(f"Найдены 2 или более БД {database_name}, сканирование проводиться не будет")
            self._databases.append(database)

    def _scan_application(self, application):
        print(f"scanning {application.name}")

    def _scan_database(self, database):
        print(f"scanning {database.name}")

    def run_scanning(self):
        for application in self._applications:
            self._scan_application(application)
        for database in self._databases:
            self._scan_database(database)
