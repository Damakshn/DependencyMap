"""
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, SmallInteger, String, DateTime, Text, Boolean
from sqlalchemy import ForeignKey

engine = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()

class SystemEntity(Base):
    """
    Компоненты исследуемой информационной системы.
    """
    __tablename__ = "SystemEntity"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    last_update = Column(DateTime)
    type = Column(Integer)

    __mapper_args__ = {
        "polymorphic_on":"type",
        "polymorphic_identity":"SystemEntity"
    }


class Network(Base):
    """
    Связи между объектами SystemEntity.    
    """
    __tablename__ = "Network"
    id = Column(Integer, primary_key=True)
    # какие сущности соединены
    start = Column(ForeignKey("SystemEntity.id"))
    end = Column(ForeignKey("SystemEntity.id"))
    comment = Column(Text)
    # если is_verified True, то связь считается подтверждённой
    # подтверждённая связь не будет стёрта при обновлении
    # у связей, созданных автоматически is_verified по умолчанию False,
    # у созданных вручную - True
    is_verified = Column(Boolean, default=False)
    # если True, то связь считается сломаной
    # это поле необходимо на первое время для тестов
    # сломанная связь не будет стёрта при обновлении и не будет отображаться
    # и не будет использоваться при поиске зависимостей
    is_broken = Column(Boolean, default=False)
    # что эта связь показывает, что self.start делает с self.end
    action = Column(String(100))

    def __repr__(self):
        mark = "⃝"
        if self.is_verified:
            mark = " ✓"
        if self.is_broken:
            mark = " ❗"
        return "Связь от " + self.start.name + " к " + self.end.name + mark


class Database(Base):
    """
    База данных в исследуемой системе
    """
    __tablename__ = "Database"
    id = Column(SmallInteger, primary_key=True)
    name = Column(String(50))

    def __repr__(self):
        return "База данных " + self.name


class Application(SystemEntity):
    """
    Клиентское приложение, написанное на Delphi.
    """
    __tablename__ = "Application"
    id = Column(Integer, ForeignKey("SystemEntity.id"), primary_key=True)
    path = Column(String(1000))

    def __repr__(self):
        return "АРМ " + self.name


class DelphiForm(SystemEntity):
    """
    Delphi-форма с компонентами.
    """
    __tablename__ = "DelphiForm"
    application = Column(ForeignKey("Application.id"))
    path = Column(String(1000))

    def __repr__(self):
        return "Форма " + self.name + " (АРМ +" + self.application.name + ")"


class ClientConnection(Base):
    """
    Компонент-соединение, с помощью которого АРМ обращается к БД.
    Учёт соединений необходим для того, чтобы знать, в контексте какой
    базы данных выполняются запросы от компонентов на формах.
    """
    __tablename__ = "Connection"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    application = Column(ForeignKey("Application.id"))
    database = Column(ForeignKey("Database.id"))
    # если True, то данные соединения проверены вручную
    # и связи подключённых к нему компонентов можно анализировать
    is_verified = Column(Boolean, default=False)

    def __repr__(self):
        return "Соединение с " + self.database.name + " ✓" if self.is_verified else " ✗"


class SQLQuery(SystemEntity):
    """
    Обобщённый SQL-запрос.
    """
    __tablename__ = "SQLQuery"
    id = Column(ForeignKey("SystemEntity.id"), primary_key=True)
    sql = Column(Text)
    database = Column(ForeignKey("Database.id"))
    lines = Column(Integer)

    def __repr__(self):
        return "Запрос/компонент " + self.name


class ClientQuery(SQLQuery):
    """
    Компонент Delphi, содержащий SQL-запрос.
    """
    __tablename__ = "ClientQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    form = Column(ForeignKey("DelphiForm.id"))
    component_name = Column(String(100))


class DBQuery(SQLQuery):
    """
    Процедура/функция/представление из базы данных исследуемой системы.
    """
    __tablename__ = "DBQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    type = Column(String(25))

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity":"DBQuery"
    }

    def __repr__(self):
        "Объект " + self.name + " (" + self.database + ")"


class DBView(DBQuery):
    """
    Представление базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"DBView"
    }

    def __repr__(self):
        "Представление " + self.name + " (" + self.database + ")"


class DBScalarFunction(DBQuery):
    """
    Скалярная функция базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"DBScalarFunction"
    }

    def __repr__(self):
        "Скалярная функция " + self.name + " (" + self.database + ")"


class DBTableFunction(DBQuery):
    """
    Табличная функция базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"DBTableFunction"
    }

    def __repr__(self):
        "Табличная функция " + self.name + " (" + self.database + ")"


class DBStoredProcedure(DBQuery):
    """
    Хранимая процедура базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"DBStoredProcedure"
    }

    def __repr__(self):
        "Хранимая процедура " + self.name + " (" + self.database + ")"


class DBTable(SystemEntity):
    """
    Таблица из базы данных исследуемой системы.
    """
    __tablename__ = "DBTable"
    id = Column(ForeignKey("SystemEntity.id"), primary_key=True)
    sql = Column(Text)
