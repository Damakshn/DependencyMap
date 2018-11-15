from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import BaseDPM, Database

class Connector:

    def __init__(self, **config):
        if "url_dpm" not in config:
            self.url_dpm = 'sqlite:///db.sqlite'
        else:
            self.url_dpm = config["url_dpm"]
        # вытащить из конфига данные для подключения к боевому серверу
        self.__sqlserver_user = config.get("username")
        self.__sqlserver_pswd = config.get("password")
        self.__sqlserver_url = config.get("server_url")
        self.__sessionmaker_dpm = None
        self.__makers = {}
    
    def connect_to_dpm(self):
        if self.__sessionmaker_dpm is None:
            engine = create_engine(self.url_dpm, echo=False)
            BaseDPM.metadata.create_all(engine)
            self.__sessionmaker_dpm = sessionmaker(bind=engine)
        return self.__sessionmaker_dpm()
    
    def connect_to(self, sysdb):
        """
        Метод для соединения с произвольной БД основной информационной системы.
        Принимает либо инстанс модели Database, либо строку с именем базы.
        """
        if isinstance(sysdb, Database):
            maker = sysdb.name
        else:
            maker = sysdb
        if maker not in self.__makers:
            pass
            # create engine (needs server credentials from config)
            # create sessionmaker (use core?)
        return self.__makers[maker]()

__all__ = ["Connector"]
