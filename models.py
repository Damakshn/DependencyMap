from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import deferred, sessionmaker, relationship
from sqlalchemy import event

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
    name = Column(String(120), nullable=False)
    last_update = Column(DateTime, nullable=False)
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
    from_node_id = Column(Integer, ForeignKey("Node.id"), nullable=False)
    from_node = relationship("Node", foreign_keys=[from_node_id])
    to_node_id = Column(Integer, ForeignKey("Node.id"), nullable=False)
    to_node = relationship("Node", foreign_keys=[to_node_id])
    comment = Column(Text)
    # если is_verified True, то связь считается подтверждённой
    # подтверждённая связь не будет стёрта при обновлении
    # у связей, созданных автоматически is_verified по умолчанию False,
    # у созданных вручную - True
    is_verified = Column(Boolean, default=False, nullable=False)
    # если True, то связь считается сломаной
    # это поле необходимо на первое время для тестов
    # сломанная связь не будет стёрта при обновлении и не будет отображаться
    # и не будет использоваться при поиске зависимостей
    is_broken = Column(Boolean, default=False, nullable=False)
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
        return f"{self.from_node.full_name} -> {self.to_node.full_name}"

# добавляем классу Node зависимости от Link
# входящие и исходящие связи
Node.links_in = relationship("Link", foreign_keys=[Link.to_node_id])
Node.links_out = relationship("Link", foreign_keys=[Link.from_node_id])

class SQLQuery(Node):
    """
    Обобщённый SQL-запрос.
    """
    # ToDo: узнать, можно ли получить сразу связи вверх и связи вниз
    __tablename__ = "SQLQuery"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    sql = deferred(Column(Text, nullable=False))
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database")

    __mapper_args__ = {
        "polymorphic_identity":"SQL-запрос"
    }

    def __repr__(self):
        return self.name


class ClientQuery(SQLQuery):
    """
    Компонент Delphi, содержащий SQL-запрос.
    """
    __tablename__ = "ClientQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    form_id = Column(ForeignKey("DelphiForm.id"), nullable=False)
    form = relationship("DelphiForm")
    component_type = Column(String(120), nullable=False)
    connection_id = Column(ForeignKey("ClientConnection.id"), nullable=False)
    connection = relationship("ClientConnection", back_populates="components")
    database = relationship("Database", back_populates="client_components")

    __mapper_args__ = {
        "polymorphic_identity":"Клиентский запрос"
    }

    @property
    def full_name(self):
        return f"{self.form.application.name}.{self.form.name}.{self.name}"

    def __repr__(self):
        return f"{self.name}: {self.component_type} "

class DelphiForm(Node):
    """
    Delphi-форма с компонентами.
    """
    __tablename__ = "DelphiForm"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    application_id = Column(ForeignKey("Application.id"), nullable=False)
    application = relationship("Application", foreign_keys=[application_id])
    path = Column(String(1000), nullable=False)
    components = relationship("ClientQuery", back_populates="form", foreign_keys=[ClientQuery.form_id])

    __mapper_args__ = {
        "polymorphic_identity":"Форма"
    }


class Application(Node):
    """
    Клиентское приложение, написанное на Delphi.
    """
    __tablename__ = "Application"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    path_to_dproj = Column(String(1000), nullable=False)
    forms = relationship("DelphiForm", back_populates="application", foreign_keys=[DelphiForm.application_id])
    connections = relationship("ClientConnection", back_populates="application")

    __mapper_args__ = {
        "polymorphic_identity":"АРМ"
    }


class Database(Base):
    """
    База данных в исследуемой системе
    """
    __tablename__ = "Database"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    tables = relationship("DBTable", back_populates="database")
    executables = relationship("DBQuery", back_populates="database")
    client_components = relationship("ClientQuery", back_populates="database")
    connections = relationship("ClientConnection", back_populates="database")

    def __repr__(self):
        return self.name


class ClientConnection(Base):
    """
    Компонент-соединение, с помощью которого АРМ обращается к БД.
    Учёт соединений необходим для того, чтобы знать, в контексте какой
    базы данных выполняются запросы от компонентов на формах.
    """
    __tablename__ = "ClientConnection"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    application_id = Column(ForeignKey("Application.id"), nullable=False)
    application = relationship("Application", back_populates="connections")
    # заполняется при создании из компонента
    database_name = Column(String(50), nullable=False)
    # ссылка на конкретную базу устанавливается в ходе верификации
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database", back_populates="connections")
    components = relationship("ClientQuery", back_populates="connection")
    # если is_verified True, то данные соединения проверены вручную
    # и связи подключённых к нему компонентов можно анализировать
    is_verified = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"Соединение {self.name} ({'???' if self.database is None else self.database.name})"


class DBQuery(SQLQuery):
    """
    Процедура/функция/представление из базы данных исследуемой системы.
    """
    __tablename__ = "DBQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    database = relationship("Database", back_populates="executables")
    schema = Column(String(30), default="dbo", nullable=False)

    @property
    def full_name(self):
        return f"{self.database.name}.{self.schema}.{self.name}"

    __mapper_args__ = {
        "polymorphic_identity":"Запрос в БД"
    }

    def __repr__(self):
        return f"{self.full_name} : Запрос"


class DBView(DBQuery):
    """
    Представление базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"Представление"
    }

    def __repr__(self):
        return f"{self.full_name} : Представление"


class DBScalarFunction(DBQuery):
    """
    Скалярная функция базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"Скалярная функция"
    }

    def __repr__(self):
        return f"{self.full_name} : Скалярная функция"


class DBTableFunction(DBQuery):
    """
    Табличная функция базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"Табличная функция"
    }

    def __repr__(self):
        return f"{self.full_name} : Табличная функция"


class DBStoredProcedure(DBQuery):
    """
    Хранимая процедура базы данных.
    """
    __mapper_args__ = {
        "polymorphic_identity":"Хранимая процедура"
    }

    def __repr__(self):
        return f"{self.full_name} : Хранимая процедура"


class DBTable(Node):
    """
    Таблица из базы данных исследуемой системы.
    """
    __tablename__ = "DBTable"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    definition = deferred(Column(Text, nullable=False))
    schema = Column(String(30), nullable=False, default="dbo")
    database_id = Column(ForeignKey("Database.id"), nullable=False)
    database = relationship("Database", back_populates="tables")

    __mapper_args__ = {
        "polymorphic_identity":"Таблица"
    }

    @property
    def full_name(self):
        return f"{self.database.name}.{self.schema}.{self.name}"

    def __repr__(self):
        return f"{self.full_name} : Таблица"


@event.listens_for(ClientConnection.is_verified, 'set')
def toggle_components(target, value, oldvalue, initiator):
    """
    Событие срабатывает при изменении атрибута is_verified,
    если True, то во всех связанных компонентах прописывается та же БД, что
    и в соединении.
    """
    if value:
        if target.database is None:
            raise Exception("База данных не указана, соединение нельзя верифицировать.")
        for item in target.components:
            item.database = target.database

Base.metadata.create_all(engine)