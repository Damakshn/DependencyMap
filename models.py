from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import deferred, sessionmaker, relationship

engine = create_engine('sqlite:///:memory:')
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class Node(Base):
    """
    Компоненты исследуемой информационной системы.
    """
    __tablename__ = "Node"
    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    last_update = Column(DateTime)
    type = Column(String(50))

    __mapper_args__ = {
        "polymorphic_on":"type",
        "polymorphic_identity":"Объект"
    }

    def get_formatted_update_date(self):
        return self.last_update.strftime("%d.%m.%Y %H:%M")


class Link(Base):
    """
    Связи между объектами Node.
    """
    __tablename__ = "Link"
    id = Column(Integer, primary_key=True)
    # какие сущности соединены
    from_node_id = Column(Integer, ForeignKey("Node.id"))
    from_node = relationship("Node", foreign_keys=[from_node_id])
    to_node_id = Column(Integer, ForeignKey("Node.id"))
    to_node = relationship("Node", foreign_keys=[to_node_id])
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
    # поле хранит битовую маску, порядок битов такой
    # contain call delete update insert select
    action = Column(Integer)

    @property
    def actions(self):
        """
        Декодирует биты из поля action.
        """
        return {
            "select": (self.action & 0b1) > 0,
            "insert": (self.action & 0b10) > 0,
            "update": (self.action & 0b100) > 0,
            "delete": (self.action & 0b1000) > 0,
            "call": (self.action & 0b10000) > 0,
            "contain": (self.action & 0b100000) > 0,
        }

    def __repr__(self):
        # обычная связь - ⃝, подтверждённая - ✓, сломанная - ⚠.
        mark = "⃝"
        if self.is_verified:
            mark = " ✓"
        if self.is_broken:
            mark = " ⚠"
        return "Связь от " + self.start.name + " к " + self.end.name + mark

class SQLQuery(Node):
    """
    Обобщённый SQL-запрос.
    """
    # ToDo: узнать, можно ли получить сразу связи вверх и связи вниз
    __tablename__ = "SQLQuery"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    sql = deferred(Column(Text))
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database")

    __mapper_args__ = {
        "polymorphic_identity":"SQL-запрос"
    }

    def __repr__(self):
        return "Запрос/компонент " + self.name


class ClientQuery(SQLQuery):
    """
    Компонент Delphi, содержащий SQL-запрос.
    """
    # ToDo: запретить создание без коннекшена
    # ToDo: фабричный метод, создающий из компонента
    __tablename__ = "ClientQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    form_id = Column(ForeignKey("DelphiForm.id"))
    form = relationship("DelphiForm")
    component_type = Column(String(120))
    connection_id = Column(ForeignKey("ClientConnection.id"))
    connection = relationship("ClientConnection", back_populates="components")
    database = relationship("Database", back_populates="client_components")

    __mapper_args__ = {
        "polymorphic_identity":"Клиентский запрос"
    }

    def __repr__(self):
        return f"{self.name}: {self.component_type} "

class DelphiForm(Node):
    """
    Delphi-форма с компонентами.
    """
    # ToDo: добавить отношение к компонентам
    __tablename__ = "DelphiForm"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    application_id = Column(ForeignKey("Application.id"))
    application = relationship("Application", foreign_keys=[application_id])
    path = Column(String(1000))
    components = relationship("ClientQuery", back_populates="form", foreign_keys=[ClientQuery.form_id])

    __mapper_args__ = {
        "polymorphic_identity":"Форма"
    }

    def __repr__(self):
        return "Форма «" + self.name + "» (АРМ " + self.application.name + ")"



class Application(Node):
    """
    Клиентское приложение, написанное на Delphi.
    """
    # ToDo: добавить отношение к формам
    __tablename__ = "Application"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    path_to_dproj = Column(String(1000))
    forms = relationship("DelphiForm", back_populates="application", foreign_keys=[DelphiForm.application_id])
    connections = relationship("ClientConnection", back_populates="application")

    __mapper_args__ = {
        "polymorphic_identity":"АРМ"
    }

    def __repr__(self):
        return "АРМ " + self.name


class Database(Base):
    """
    База данных в исследуемой системе
    """
    __tablename__ = "Database"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    tables = relationship("DBTable", back_populates="database")
    executables = relationship("DBQuery", back_populates="database")
    client_components = relationship("ClientQuery", back_populates="database")
    connections = relationship("ClientConnection", back_populates="database")

    def __repr__(self):
        return "База данных " + self.name


class ClientConnection(Base):
    """
    Компонент-соединение, с помощью которого АРМ обращается к БД.
    Учёт соединений необходим для того, чтобы знать, в контексте какой
    базы данных выполняются запросы от компонентов на формах.
    """
    # ToDo: фабричный метод, создающий из компонента
    __tablename__ = "ClientConnection"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    application_id = Column(ForeignKey("Application.id"))
    application = relationship("Application", back_populates="connections")
    # заполняется при создании из компонента
    database_name = Column(String(50))
    # ссылка на конкретную базу устанавливается в ходе верификации
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database", back_populates="connections")
    components = relationship("ClientQuery", back_populates="connection")
    # если is_verified True, то данные соединения проверены вручную
    # и связи подключённых к нему компонентов можно анализировать
    is_verified = Column(Boolean, default=False)

    def __repr__(self):
        return "Соединение " + self.name + "(" + self.database.name + ")"


class DBQuery(SQLQuery):
    """
    Процедура/функция/представление из базы данных исследуемой системы.
    """
    __tablename__ = "DBQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    database = relationship("Database", back_populates="executables")
    schema = Column(String(30), default="dbo")

    __mapper_args__ = {
        "polymorphic_identity":"Запрос в БД"
    }

    def __repr__(self):
        return "Объект " + self.name + " (" + self.database.name + ")"


class DBView(DBQuery):
    """
    Представление базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"Представление"
    }

    def __repr__(self):
        return "Представление " + self.name + " (" + self.database.name + ")"


class DBScalarFunction(DBQuery):
    """
    Скалярная функция базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"Скалярная функция"
    }

    def __repr__(self):
        return "Скалярная функция " + self.name + " (" + self.database.name + ")"


class DBTableFunction(DBQuery):
    """
    Табличная функция базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"Табличная функция"
    }

    def __repr__(self):
        return "Табличная функция " + self.name + " (" + self.database.name + ")"


class DBStoredProcedure(DBQuery):
    """
    Хранимая процедура базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"Хранимая процедура"
    }

    def __repr__(self):
        return "Хранимая процедура " + self.name + " (" + self.database.name + ")"


class DBTable(Node):
    """
    Таблица из базы данных исследуемой системы.
    """
    __tablename__ = "DBTable"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    definition = deferred(Column(Text))
    schema = Column(String(30))
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database", back_populates="tables")

    __mapper_args__ = {
        "polymorphic_identity":"Таблица"
    }

    def __repr__(self):
        return "Таблица " + self.name + " (" + self.database.name + ")"

Base.metadata.create_all(engine)
