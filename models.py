from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime

engine = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()

class SystemEntity(Base):
    """
    Компоненты исследуемой информационной системы.
    """
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    last_update = Column(DateTime)


class Network(Base):
    """
    Связи между объектами SystemEntity.
    """
    pass


class Database(SystemEntity):
    """
    База данных в исследуемой системе
    """
    pass


class DelphiApp(SystemEntity):
    """
    Клиентское приложение, написанное на Delphi.
    """
    pass


class DelphiForm(Base):
    """
    Delphi-форма с компонентами.
    """
    pass


class ClientConnection(Base):
    """
    Компонент-соединение, с помощью которого АРМ обращается к БД.
    """
    pass


class ClientQuery(SystemEntity):
    """
    Компонент Delphi, содержащий SQL-запрос.
    """
    pass


class DBTable(SystemEntity):
    """
    Таблица из базы данных исследуемой системы.
    """
    pass


class DBQuery(SystemEntity):
    """
    Процедура/функция/представление из базы данных исследуемой системы.
    """
    pass