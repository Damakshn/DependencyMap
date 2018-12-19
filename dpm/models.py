from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Boolean, event
from sqlalchemy.orm import deferred, relationship
from sync.common_classes import Synchronizable
import binascii
import datetime


BaseDPM = declarative_base()


class ModelException(Exception):
    pass

# todo почистить по возможности цепочки наследования
# todo вес запросов (строки, байты или ещё что-то)
# todo почему данные не перезаписываются, а дублируются


class Node(BaseDPM, Synchronizable):
    """
    Компоненты исследуемой информационной системы.
    """
    __tablename__ = "Node"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    # когда последний раз обновлялись связи
    last_revision = Column(DateTime)
    # когда последний раз сверялись с оригиналом
    last_sync = Column(DateTime, default=datetime.datetime.now)
    type = Column(String(50))

    __mapper_args__ = {
        "polymorphic_on":"type",
        "polymorphic_identity":"Объект"
    }

    @classmethod
    def key_field(cls):
        """
        Возвращает имя атрибута, значения которого можно использовать
        при сопоставлении с оригиналами из исходников во время синхронизации.
        """
        return "name"
    
    def update_from(self, original):
        """
        Обновляет данные основных полей объекта данными из исходников.
        """
        # проверяем наличие всех синхронизируемых полей в оригинале
        for field in self.sync_fields:
            if not hasattr(original, field):
                raise ModelException(f"Поле {field} не найдено в оригинале объекта {self.__class__}")
        for field in self.sync_fields:
            setattr(self, field, getattr(original, field))
        self.last_sync = datetime.datetime.now()

    @classmethod
    def create_from(cls, original, **refs):
        raise NotImplementedError(f"Метод create_from не реализован для класса {cls}")

    @property
    def sync_fields(self):
        return []

    @property
    def is_root(self):
        """
        Возвращает True, если узел является корневым, т.е. у него не бывает
        входящих связей, только исходящие.
        """
        return False

    def get_formatted_update_date(self):
        return self.last_revision.strftime("%d.%m.%Y %H:%M")


class Link(BaseDPM):
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
    """ 
    contain = Column(Boolean, default=False)
    call = Column(Boolean, default=False)
    select = Column(Boolean, default=False)
    insert = Column(Boolean, default=False)
    update = Column(Boolean, default=False)
    delete = Column(Boolean, default=False)
    truncate = Column(Boolean, default=False)
    drop = Column(Boolean, default=False)
    multiple = Column(Boolean, default=False)
    unknown = Column(Boolean, default=False)
    """

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


class SourceCodeFile(Node):
    """
    Файл с исходниками программы, хранящийся на диске.
    При синхронизации идентифицируется по пути к нему.
    """
    __tablename__ = "SourceCodeFile"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    path = Column(String(1000), nullable=False)
    last_update = Column(DateTime)

    @property
    def sync_fields(self):
        return ["last_update"]
    
    @classmethod
    def key_field(cls):
        """
        Возвращает имя атрибута, значения которого можно использовать
        при сопоставлении с оригиналами из исходников во время синхронизации.
        """
        return "path"
    
    __mapper_args__ = {
        "polymorphic_identity":"Файл с программным кодом"
    }

class DatabaseObject():
    # id объекта в оригинальной базе (для точечного обновления)
    database_object_id = Column(Integer, nullable=False)
    schema = Column(String(30), nullable=False, default="dbo")
    last_update = Column(DateTime)


class SQLQuery(Node):
    """
    Обобщённый SQL-запрос.
    """
    __tablename__ = "SQLQuery"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    sql = deferred(Column(Text, nullable=False))
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database", foreign_keys=[database_id])
    crc32 = Column(Integer)

    @property
    def sync_fields(self):
        return ["sql"]

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
    form_id = Column(ForeignKey("Form.id"), nullable=False)
    form = relationship("Form")
    component_type = Column(String(120), nullable=False)
    connection_id = Column(ForeignKey("ClientConnection.id"))
    connection = relationship("ClientConnection", back_populates="components")
    database = relationship("Database", foreign_keys=[SQLQuery.database_id], back_populates="client_components")

    __mapper_args__ = {
        "polymorphic_identity":"Клиентский запрос"
    }

    @property
    def sync_fields(self):
        return ["sql", "component_type"]

    @classmethod
    def create_from(cls, original, **refs):
        """
        Собирает ORM-модель для компонента Delphi.
        Исходные данные берутся из оригинального компонента с диска,
        к модели присоединяются ссылки на форму и на соединение с БД.
        """
        for param in ["parent", "connections"]:
            if param not in refs:
                raise ModelException(f"Пропущен именованный параметр {param}")
        if original.connection is not None and original.connection not in refs["connections"]:
            appname = refs["parent"].application.name
            raise ModelException(f"Соединение {original.connection} не найдено в пуле соединений приложения {appname}")
        return ClientQuery(
            name=original.name,
            sql=original.sql,
            component_type=original.type,
            connection=refs["connections"].get(original.connection, None),
            form=refs["parent"]
        )

    def __repr__(self):
        return f"{self.name}: {self.component_type} "

class Form(SourceCodeFile):
    """
    Delphi-форма с компонентами.
    """
    __tablename__ = "Form"
    id = Column(Integer, ForeignKey("SourceCodeFile.id"), primary_key=True)
    alias = Column(String(50))
    application_id = Column(ForeignKey("Application.id"), nullable=False)
    application = relationship("Application", foreign_keys=[application_id])
    components = relationship("ClientQuery", back_populates="form", foreign_keys=[ClientQuery.form_id])
    is_broken = Column(Boolean, default=False, nullable=False)
    parsing_error_message = Column(String(300))

    __mapper_args__ = {
        "polymorphic_identity":"Форма"
    }

    @property
    def sync_fields(self):
        return ["last_update", "alias", "is_broken", "parsing_error_message"]

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
            application=refs["parent"],
            path=original.path,
            is_broken=original.is_broken,
            parsing_error_message=original.parsing_error_message
        )

    def __repr__(self):
        return self.name

class ClientConnection(Node):
    """
    Компонент-соединение, с помощью которого АРМ обращается к БД.
    Учёт соединений необходим для того, чтобы знать, в контексте какой
    базы данных выполняются запросы от компонентов на формах.
    """
    __tablename__ = "ClientConnection"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    application_id = Column(ForeignKey("Application.id"), nullable=False)
    application = relationship("Application", foreign_keys=[application_id], back_populates="connections")
    # заполняется при создании из компонента
    database_name = Column(String(50))
    # ссылка на конкретную базу устанавливается в ходе верификации
    database_id = Column(ForeignKey("Database.id"))
    database = relationship("Database", back_populates="connections", foreign_keys=[database_id])
    components = relationship("ClientQuery", back_populates="connection", foreign_keys=[ClientQuery.connection_id])
    # если is_verified True, то данные соединения проверены вручную
    # и связи подключённых к нему компонентов можно анализировать
    is_verified = Column(Boolean, default=False, nullable=False)

    @property
    def sync_fields(self):
        return ["database_name"]

    @classmethod
    def create_from(cls, original, **refs):
        if "parent" not in refs:
            raise ModelException("Пропущен именованный параметр parent")
        return ClientConnection(
            name=original.full_name,
            database_name=original.database,
            application=refs["parent"]
        )

    def __repr__(self):
        return f"Соединение {self.name} ({'???' if self.database is None else self.database.name})"


class Application(SourceCodeFile):
    """
    Клиентское приложение, написанное на Delphi.
    """
    __tablename__ = "Application"
    id = Column(Integer, ForeignKey("SourceCodeFile.id"), primary_key=True)
    forms = relationship("Form", back_populates="application", foreign_keys=[Form.application_id])
    connections = relationship(
        "ClientConnection",
        back_populates="application",
        foreign_keys=[ClientConnection.application_id])

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
            last_update=original.last_update,
            path=original.path
        )

    def __repr__(self):
        return self.name


class DBQuery(SQLQuery, DatabaseObject):
    """
    Процедура/функция/представление из базы данных исследуемой системы.
    """
    __tablename__ = "DBQuery"
    id = Column(ForeignKey("SQLQuery.id"), primary_key=True)
    database = relationship("Database", back_populates="executables", foreign_keys=[SQLQuery.database_id])

    @property
    def full_name(self):
        return f"{self.database.name}.{self.schema}.{self.name}"

    __mapper_args__ = {
        "polymorphic_identity":"Запрос в БД"
    }

    def __repr__(self):
        return f"{self.full_name} : Запрос"
    
    @classmethod
    def create_from(cls, original, **refs):
        """
        Собирает ORM-модель для исполняемого объекта БД.
        Исходные данные берутся из системных таблиц исследуемой базы,
        к модели присоединяется ссылка на базу информационной системы.
        """
        if "parent" not in refs:
            raise ModelException("Пропущен именованный параметр parent")
        return cls(
            name=original.name,
            schema=original.schema,
            sql=original.sql,
            last_update=original.last_update,
            database_object_id=original.database_object_id,
            database=refs["parent"]
        )


class DBView(DBQuery):
    """
    Представление базы данных.
    """
    __tablename__ = "DBView"
    id = Column(ForeignKey("DBQuery.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity":"Представление"
    }

    def __repr__(self):
        return f"{self.full_name} : Представление"


class DBScalarFunction(DBQuery):
    """
    Скалярная функция базы данных.
    """
    __tablename__ = "DBScalarFunction"
    id = Column(ForeignKey("DBQuery.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity":"Скалярная функция"
    }

    def __repr__(self):
        return f"{self.full_name} : Скалярная функция"


class DBTableFunction(DBQuery):
    """
    Табличная функция базы данных.
    """
    __tablename__ = "DBTableFunction"
    id = Column(ForeignKey("DBQuery.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity":"Табличная функция"
    }

    def __repr__(self):
        return f"{self.full_name} : Табличная функция"


class DBStoredProcedure(DBQuery):
    """
    Хранимая процедура базы данных.
    """
    __tablename__ = "DBStoredProcedure"
    id = Column(ForeignKey("DBQuery.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity":"Хранимая процедура"
    }

    def __repr__(self):
        return f"{self.full_name} : Хранимая процедура"


class DBTrigger(DBQuery):
    """
    Триггер, привязанный к таблице.
    """
    __tablename__ = "DBTrigger"
    id = Column(ForeignKey("DBQuery.id"), primary_key=True)
    table_id = Column(ForeignKey("DBTable.id"), nullable=False)
    table = relationship("DBTable", back_populates="triggers", foreign_keys=[table_id])
    is_update = Column(Boolean, nullable=False)
    is_delete = Column(Boolean, nullable=False)
    is_insert = Column(Boolean, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity":"Триггер"
    }

    def __repr__(self):
        return f"{self.full_name} : Триггер"
    
    @classmethod
    def create_from(cls, original, **refs):
        for param in ["table", "database"]:
            if param not in refs:
                raise ModelException(f"Пропущен именованный параметр {param}")
        return DBTrigger(
            name=original.name,
            schema=original.schema,
            database_object_id=original.database_object_id,
            is_update=original.is_update,
            is_delete=original.is_delete,
            is_insert=original.is_insert,
            sql=original.sql,
            last_update=original.last_update,
            table=refs["table"],
            database=refs["database"]
        )

class DBTable(Node, DatabaseObject):
    """
    Таблица из базы данных исследуемой системы.
    """
    __tablename__ = "DBTable"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    database_id = Column(ForeignKey("Database.id"), nullable=False)
    database = relationship("Database", back_populates="tables", foreign_keys=[database_id])
    triggers = relationship("DBTrigger", back_populates="table", foreign_keys=[DBTrigger.table_id])

    __mapper_args__ = {
        "polymorphic_identity":"Таблица"
    }

    @property
    def full_name(self):
        return f"{self.database.name}.{self.schema}.{self.name}"

    def __repr__(self):
        return f"{self.full_name} : Таблица"
    
    @classmethod
    def create_from(cls, original, **refs):
        if "parent" not in refs:
            raise ModelException("Пропущен именованный параметр parent")
        return DBTable(
            name=original.name,
            schema=original.schema,
            database_object_id=original.database_object_id,
            last_update=original.last_update,
            database=refs["parent"]
        )


class Database(Node):
    """
    База данных в исследуемой системе
    """
    __tablename__ = "Database"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    last_update = Column(DateTime)
    tables = relationship("DBTable", back_populates="database", foreign_keys=[DBTable.database_id])
    views = relationship("DBView", back_populates="database", foreign_keys=[DBView.database_id])
    procedures = relationship("DBStoredProcedure", back_populates="database", foreign_keys=[DBStoredProcedure.database_id])
    table_functions = relationship("DBTableFunction", back_populates="database", foreign_keys=[DBTableFunction.database_id])
    scalar_functions = relationship("DBScalarFunction", back_populates="database", foreign_keys=[DBScalarFunction.database_id])
    triggers = relationship("DBTrigger", back_populates="database", foreign_keys=[DBTrigger.database_id])
    executables = relationship("DBQuery", back_populates="database", foreign_keys=[DBQuery.database_id])
    client_components = relationship("ClientQuery", back_populates="database", foreign_keys=[ClientQuery.database_id])
    connections = relationship("ClientConnection", back_populates="database", foreign_keys=[ClientConnection.database_id])

    __mapper_args__ = {
        "polymorphic_identity":"База данных"
    }

    @property
    def sync_fields(self):
        return ["last_update"]

    def __repr__(self):
        return self.name
    




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
