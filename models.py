from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import deferred, sessionmaker, relationship
from sqlalchemy import event
import binascii
import datetime

engine = create_engine('sqlite:///:memory:')
Base = declarative_base()
SessionDPM = sessionmaker(bind=engine)


class ModelException(Exception):
    pass


class DatabaseObject:
    schema = Column(String(30), nullable=False, default="dbo")


class DelphiThingReplica:
    """
    ORM-модель, подлежащая синхронизации с исходниками на Delphi.
    """
    last_sync = Column(DateTime)
    sync_fields = []

    def update_from(self, original):
        """
        Обновляет данные основных полей объекта данными из исходников.
        """
        for field in self.sync_fields:
            setattr(self, field, original[field])
        self.last_sync = datetime.datetime.now()
    
    @classmethod
    def create_from(cls, original):
        pass
    
    @classmethod
    def get_sync_key_field(cls) -> str:
        """
        Возвращает имя атрибута, значения которого можно использовать
        при сопоставлении с оригиналами из исходников во время синхронизации.
        """
        return ""


class SourceCodeFile:
    path = Column(String(1000), nullable=False)
    last_update = Column(DateTime)


class Node(Base):
    """
    Компоненты исследуемой информационной системы.
    """
    __tablename__ = "Node"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    # когда последний раз обновлялись связи
    last_revision = Column(DateTime)
    # когда последний раз сверялись с оригиналом
    last_sync = Column(DateTime, nullable=False)
    type = Column(String(50))

    __mapper_args__ = {
        "polymorphic_on":"type",
        "polymorphic_identity":"Объект"
    }

    @property
    def is_root(self):
        """
        Возвращает True, если узел является корневым, т.е. у него не бывает
        входящих связей, только исходящие.
        """
        return False

    def get_formatted_update_date(self):
        return self.last_revision.strftime("%d.%m.%Y %H:%M")


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
        if isinstance(self.from_node, DBQuery):
            from_node_name = self.from_node.full_name
        else:
            from_node_name = self.from_node.name

        if isinstance(self.to_node, DBQuery):
            to_node_name = self.to_node.full_name
        else:
            to_node_name = self.to_node.name
        return f"{from_node_name} -> {to_node_name}"

# добавляем классу Node зависимости от Link
# входящие и исходящие связи
Node.links_in = relationship("Link", foreign_keys=[Link.to_node_id])
Node.links_out = relationship("Link", foreign_keys=[Link.from_node_id])


class SQLQuery(Node):
    """
    Обобщённый SQL-запрос.
    """
    __tablename__ = "SQLQuery"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    sql = deferred(Column(Text, nullable=False))
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database")
    crc32 = Column(Integer)

    __mapper_args__ = {
        "polymorphic_identity":"SQL-запрос"
    }

    def __repr__(self):
        return self.name


class ClientQuery(SQLQuery, DelphiThingReplica):
    """
    Компонент Delphi, содержащий SQL-запрос.
    """
    __tablename__ = "ClientQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    form_id = Column(ForeignKey("Form.id"), nullable=False)
    form = relationship("Form")
    component_type = Column(String(120), nullable=False)
    connection_id = Column(ForeignKey("ClientConnection.id"))
    connection = relationship("ClientConnection", back_populates="components")
    database = relationship("Database", back_populates="client_components")
    sync_fields = ["sql"]

    __mapper_args__ = {
        "polymorphic_identity":"Клиентский запрос"
    }

    @classmethod
    def create_from(cls, original, **refs):
        # ToDo throw exception when missing form and connections in refs
        """
        Собирает ORM-модель для компонента Delphi.
        Исходные данные берутся из оригинального компонента с диска,
        к модели присоединяются ссылки на форму и на соединение с БД.
        """
        for param in ["parent", "connections"]:
            if param not in refs:
                raise ModelException(f"Пропущен именованный параметр {param}")
        if original.connection not in refs["connections"]:
            appname = refs["parent"].application.name
            raise ModelException(f"Соединение {original.connection} не найдено в пуле соединений приложения {appname}")
        return ClientQuery(
            name=original.name,
            sql=original.sql,
            component_type=original.type,
            last_sync=datetime.datetime.now(),
            connection=refs["connections"][original.connection],
            form=refs["parent"]
        )
    
    @classmethod
    def get_sync_key_field(cls):
        """
        Возвращает имя атрибута, значения которого можно использовать
        при сопоставлении с оригиналами из исходников во время синхронизации.
        """
        return "name"

    def __repr__(self):
        return f"{self.name}: {self.component_type} "

class Form(Node, SourceCodeFile, DelphiThingReplica):
    """
    Delphi-форма с компонентами.
    """
    __tablename__ = "Form"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    alias = Column(String(50))
    application_id = Column(ForeignKey("Application.id"), nullable=False)
    application = relationship("Application", foreign_keys=[application_id])
    components = relationship("ClientQuery", back_populates="form", foreign_keys=[ClientQuery.form_id])
    sync_fields = ["last_update"]

    __mapper_args__ = {
        "polymorphic_identity":"Форма"
    }
    
    @classmethod
    def create_from(cls, original, **refs):
        """
        Собирает ORM-модель для формы из данных оригинала в исходниках,
        присоединяет ссылку на АРМ.
        """
        if "parent" not in refs:
            raise ModelException("Пропущен именованный параметр parent")
        return Form(
            name=original.name,
            alias=original.alias,
            last_update=original.last_update,
            last_sync=datetime.datetime.now(),
            application=refs["parent"],
            path=original.path
        )
    
    @classmethod
    def get_sync_key_field(cls):
        """
        Возвращает имя атрибута, значения которого можно использовать
        при сопоставлении с оригиналами из исходников во время синхронизации.
        """
        return "path"
    
    def __repr__(self):
        return self.name


class Application(Node, SourceCodeFile, DelphiThingReplica):
    """
    Клиентское приложение, написанное на Delphi.
    """
    __tablename__ = "Application"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    forms = relationship("Form", back_populates="application", foreign_keys=[Form.application_id])
    connections = relationship("ClientConnection", back_populates="application")
    sync_fields = ["last_update"]

    __mapper_args__ = {
        "polymorphic_identity":"АРМ"
    }

    @property
    def is_root(self):
        """
        Возвращает True, если узел является корневым, т.е. у него не бывает
        входящих связей, только исходящие.
        """
        return True
    
    @classmethod
    def create_from(cls, original, **refs):
        return Application(
            name=original.name,
            path=original.path
        )

    @classmethod
    def get_sync_key_field(cls):
        """
        Возвращает имя атрибута, значения которого можно использовать
        при сопоставлении с оригиналами из исходников во время синхронизации.
        """
        return "path"

    def __repr__(self):
        return self.name


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
    database_name = Column(String(50))
    # ссылка на конкретную базу устанавливается в ходе верификации
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database", back_populates="connections")
    components = relationship("ClientQuery", back_populates="connection")
    # если is_verified True, то данные соединения проверены вручную
    # и связи подключённых к нему компонентов можно анализировать
    is_verified = Column(Boolean, default=False, nullable=False)
    sync_fields = ["database_name"]

    @classmethod
    def create_from(cls, original, **refs):
        if "parent" not in refs:
            raise ModelException("Пропущен именованный параметр parent")
        return ClientConnection(
            name=original.name,
            database_name=original.database_name,
            application=refs["parent"]
        )

    @classmethod
    def get_sync_key_field(cls):
        """
        Возвращает имя атрибута, значения которого можно использовать
        при сопоставлении с оригиналами из исходников во время синхронизации.
        """
        return "name"

    def __repr__(self):
        return f"Соединение {self.name} ({'???' if self.database is None else self.database.name})"


class DBQuery(DatabaseObject, SQLQuery):
    """
    Процедура/функция/представление из базы данных исследуемой системы.
    """
    __tablename__ = "DBQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    database = relationship("Database", back_populates="executables")
    #schema = Column(String(30), default="dbo", nullable=False)

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


class DBTable(DatabaseObject, Node):
    """
    Таблица из базы данных исследуемой системы.
    """
    __tablename__ = "DBTable"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    definition = deferred(Column(Text, nullable=False))
    #schema = Column(String(30), nullable=False, default="dbo")
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


@event.listens_for(SQLQuery.sql, 'set', propagate=True)
def generate_crc_for_query_object(target, value, oldvalue, initiator):
    """
    Событие срабатывает при изменениии sql-исходников любого запроса
    и автоматически генерирует контрольную сумму.
    """
    if value:
        target.crc32 = binascii.crc32(value.encode("utf-8"))

Base.metadata.create_all(engine)
