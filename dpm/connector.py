from sqlalchemy import create_engine, engine
from sqlalchemy.orm import sessionmaker
from .models import BaseDPM, Database
import pyodbc


class DriverNotFoundException(Exception):
    pass


class Connector:
    """
    Класс, отвечающий за управление соединениями с БД.
    Соединение с базой DPM и основными базами информационной системы
    обрабатываются отдельно.
    Для инициализации требует словарь-конфиг с полями:
        username_sql, password_sql, host_sql -
        для подключения к боевым базам ИС;
        host_dpm, password_dpm, host_dpm - для подключения к базе
        ДПМ (пока неактивно, используем sqlite).
    """

    def __init__(self, **config):
        if "host_dpm" not in config:
            self.url_dpm = 'sqlite:///db.sqlite'
        else:
            self.url_dpm = config["host_dpm"]
        # вытащить из конфига данные для подключения к боевому серверу
        self.__sqlserver_user = config.get("username_sql")
        self.__sqlserver_pswd = config.get("password_sql")
        self.__sqlserver_host = config.get("host_sql")
        self.__sessionmaker_dpm = None
        self.__driver_sql = self.__get_driver()
        self.__connections = {}

    def __get_driver(self):
        """
        Смотрит установленные в системе ODBC-драйверы для SQL Server
        и возвращает имя последнего установленного драйвера.
        Кидает исключение, если подходящих драйверов нет.
        """
        available_drivers = [
            driver for driver in pyodbc.drivers() if driver.find("SQL Server") >= 0
        ]
        if len(available_drivers) == 0:
            raise DriverNotFoundException("Не найден ODBC драйвер для соединения с SQL Server.")
        return available_drivers[len(available_drivers)-1]

    def connect_to_dpm(self):
        if self.__sessionmaker_dpm is None:
            engine = create_engine(self.url_dpm, echo=False)
            BaseDPM.metadata.create_all(engine)
            self.__sessionmaker_dpm = sessionmaker(bind=engine)
        return self.__sessionmaker_dpm()

    def connect_to(self, db):
        """
        Метод для соединения с произвольной БД основной информационной системы.
        Принимает либо инстанс модели Database, либо строку с именем базы.
        Возвращает объект-соединение.
        """
        if isinstance(db, Database):
            db_name = db.name
        else:
            db_name = db
        if db_name not in self.__connections:
            url = engine.url.URL(
                "mssql+pyodbc",
                username=self.__sqlserver_user,
                password=self.__sqlserver_pswd,
                host=self.__sqlserver_host,
                database=db_name,
                query=dict(driver=self.__driver_sql)
            )
            e = create_engine(url, echo=False)
            self.__connections[db_name] = e.connect()
        return self.__connections[db_name]


__all__ = ["Connector"]
