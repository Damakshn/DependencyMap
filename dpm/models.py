from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Boolean, SmallInteger, event
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.orm.collections import attribute_mapped_collection

import binascii
import datetime

BaseDPM = declarative_base()


class ModelException(Exception):
    pass


class Node(BaseDPM):
    """
    Компоненты исследуемой информационной системы.
    """
    __tablename__ = "Node"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    # когда последний раз обновлялись связи
    last_revision = Column(DateTime)
    # когда последний раз сверялись с оригиналом
    last_update = Column(DateTime)
    type = Column(String(50))

    __mapper_args__ = {
        "polymorphic_on":"type",
        "polymorphic_identity":"Объект"
    }
    
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
        self.last_update = getattr(original, "last_update", datetime.datetime.now())

    @classmethod
    def create_from(cls, original, **refs):
        """
        Создаёт экземпляр ноды из оригинала.

        refs - ссылочные параметры, в классах потомках расписаны подробно.
        """
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

    def get_formatted_revision_date(self):
        return self.last_revision.strftime("%d.%m.%Y %H:%M")
    
    def get_formatted_update_date(self):
        return self.last_update.strftime("%d.%m.%Y %H:%M")
    
    def get_regexp(self):
        """
        Получение регулярки для объекта.

        Итоговое выражение имеет такой вид:

        (?P<select>варианты для всех имён во всех контекстах)|(?P<update>...)|(?P...

        С таблицей проводятся операции select, insert, update, delete, 
        truncate, drop;

        Имя объекта может иметь следующий вид:
            * имя_объекта
            * схема.имя_объекта
            * база.схема.имя_объекта
        
        Одно и то же действие (вставка, выборка) может быть оформлено синтаксически по-разному;

        Итоговое регулярное выражение формируется как комбинация всех этих вариантов.
        """
        raise NotImplementedError(f"Метод get_regexp не определён для класса {self.__class__}")


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
    # если is_verified True, то связь считается подтверждённой;
    # подтверждённая связь не будет стёрта при обновлении;
    # у связей, созданных автоматически is_verified по умолчанию False,
    # у созданных вручную - True
    is_verified = Column(Boolean, default=False, nullable=False)
    # если is_broken True, то связь считается сломаной
    # это поле необходимо на первое время для тестов
    # сломанная связь не будет стёрта при обновлении и не будет отображаться
    # и не будет использоваться при поиске зависимостей
    is_broken = Column(Boolean, default=False, nullable=False)
    # поля, описывающие что объект from_node делает с объектом to_node
    # числовое значение указывает на число совпадений (кол-во использований)
    contain = Column(Boolean, default=False)
    call = Column(SmallInteger, default=0)
    select = Column(SmallInteger, default=0)
    insert = Column(SmallInteger, default=0)
    update = Column(SmallInteger, default=0)
    delete = Column(SmallInteger, default=0)
    truncate = Column(SmallInteger, default=0)
    drop = Column(SmallInteger, default=0)

    def __repr__(self):
        if isinstance(self.from_node, DBScript):
            from_node_name = self.from_node.full_name
        else:
            from_node_name = self.from_node.name

        if isinstance(self.to_node, DBScript):
            to_node_name = self.to_node.full_name
        else:
            to_node_name = self.to_node.name
        return f"{from_node_name} -> {to_node_name}"

# добавляем классу Node зависимости от Link
# входящие и исходящие связи
Node.links_in = relationship("Link", foreign_keys=[Link.to_node_id])
Node.links_out = relationship("Link", foreign_keys=[Link.from_node_id])


class SourceCodeFileMixin():
    """
    Файл с исходниками программы, хранящийся на диске.
    """
    path = Column(String(1000), nullable=False)

class DatabaseObject(Node):
    __tablename__ = "DatabaseObject"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    database_id = Column(ForeignKey("Database.id"))
    # имя базы данных добавлено для того, чтобы не провоцировать срабатывание 
    # session.flush при запросе свойства full_name
    database_name = Column(String(120), nullable=False)
    database = relationship("Database", foreign_keys=[database_id])
    # id объекта в оригинальной базе (для точечного обновления)
    database_object_id = Column(Integer, nullable=False)
    schema = Column(String(30), nullable=False)

    @property
    def long_name(self):
        return f"{self.schema}.{self.name}"
    
    @property
    def full_name(self):
        return f"{self.database_name}.{self.schema}.{self.name}"


class SQLQueryMixin():
    """
    Произвольный SQL-запрос.
    """
    crc32 = Column(Integer)
    @declared_attr
    def sql(cls):
        return deferred(Column(Text, nullable=False))


class ClientQuery(Node, SQLQueryMixin):
    """
    Компонент Delphi, содержащий SQL-запрос.
    """
    __tablename__ = "ClientQuery"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    form_id = Column(ForeignKey("Form.id"), nullable=False)
    form = relationship("Form", foreign_keys=[form_id])
    component_type = Column(String(120), nullable=False)
    connection_id = Column(ForeignKey("ClientConnection.id"))
    connection = relationship(
        "ClientConnection",
        foreign_keys=[connection_id],
        back_populates="components")

    __mapper_args__ = {
        "polymorphic_identity":"Клиентский запрос"
    }

    @property
    def sync_fields(self):
        return ["sql", "component_type", "crc32"]

    @classmethod
    def create_from(cls, original, **refs):
        """
        Собирает ORM-модель для компонента Delphi.
        Исходные данные берутся из оригинального компонента с диска,
        к модели присоединяются ссылки на форму и на соединение с БД.

        Дата обновления ставится немножко костыльно, так как узнать реальную дату
        обновления компонента невозможно.
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
            last_update=datetime.datetime.now(),
            crc32=original.crc32,
            connection=refs["connections"].get(original.connection, None),
            form=refs["parent"]
        )

    def __repr__(self):
        return f"{self.name}: {self.component_type} "

class Form(Node, SourceCodeFileMixin):
    """
    Delphi-форма с компонентами.
    """
    __tablename__ = "Form"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    alias = Column(String(50))
    application_id = Column(ForeignKey("Application.id"), nullable=False)
    application = relationship(
        "Application",
        foreign_keys=[application_id],
        back_populates="forms")
    components = relationship(
        "ClientQuery",
        collection_class=attribute_mapped_collection("name"),
        back_populates="form",
        foreign_keys=[ClientQuery.form_id])
    # на случай, если форму не удалось распарсить
    is_broken = Column(Boolean, default=False, nullable=False)
    parsing_error_message = Column(String(300))

    __mapper_args__ = {
        "polymorphic_identity":"Форма"
    }

    @property
    def sync_fields(self):
        return ["alias", "is_broken", "parsing_error_message"]

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
            path=original.path,
            application=refs["parent"],
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
    components = relationship(
        "ClientQuery",
        collection_class=attribute_mapped_collection("name"),
        back_populates="connection",
        foreign_keys=[ClientQuery.connection_id])
    # если is_verified True, то данные соединения проверены вручную
    # и связи подключённых к нему компонентов можно анализировать
    is_verified = Column(Boolean, default=False, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity":"Компонент-соединение"
    }

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


class Application(Node, SourceCodeFileMixin):
    """
    Клиентское приложение, написанное на Delphi.
    """
    __tablename__ = "Application"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    forms = relationship(
        "Form",
        collection_class=attribute_mapped_collection("path"),
        back_populates="application",
        foreign_keys=[Form.application_id])
    connections = relationship(
        "ClientConnection",
        collection_class=attribute_mapped_collection("name"),
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


class DBScript(DatabaseObject, SQLQueryMixin):
    """
    Процедура/функция/представление из базы данных исследуемой системы.
    """
    __tablename__ = "DBScript"
    id = Column(Integer, ForeignKey("DatabaseObject.id"), primary_key=True)
    database = relationship(
        "Database",
        back_populates="executables",
        foreign_keys=[DatabaseObject.database_id])
    references = relationship(
        "SystemReference",
        collection_class=attribute_mapped_collection("database_object_id"),
        back_populates="script")

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
            database_name=refs["parent"].name,
            sql=original.sql,
            crc32=original.crc32,
            last_update=original.last_update,
            database_object_id=original.database_object_id,
            database=refs["parent"]
        )
    
    @property
    def sync_fields(self):
        return ["sql", "crc32"]
    
    def get_regexp(self):
        return []


class SystemReference(BaseDPM):
    """
    Зависимость между объектами БД, подтянутая из системных таблиц
    SQL Server.
    """
    __tablename__ = "SystemReference"
    id = Column(Integer, primary_key=True)
    script_id = Column(Integer, ForeignKey("DBScript.id"), nullable=False)
    script = relationship(
        "DBScript",
        back_populates="references")
    # id объекта, от которого зависит скрипт
    database_object_id = Column(Integer, nullable=False)
    # ставится в True после проверки скрипта алгоритмом анализа связей
    is_checked = Column(Boolean, nullable=False, default=False)


class DBView(DBScript):
    """
    Представление базы данных.
    """
    __tablename__ = "DBView"
    id = Column(ForeignKey("DBScript.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity":"Представление"
    }

    def __repr__(self):
        return f"{self.full_name} : Представление"


class DBScalarFunction(DBScript):
    """
    Скалярная функция базы данных.
    """
    __tablename__ = "DBScalarFunction"
    id = Column(ForeignKey("DBScript.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity":"Скалярная функция"
    }

    def __repr__(self):
        return f"{self.full_name} : Скалярная функция"


class DBTableFunction(DBScript):
    """
    Табличная функция базы данных.
    """
    __tablename__ = "DBTableFunction"
    id = Column(ForeignKey("DBScript.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity":"Табличная функция"
    }

    def __repr__(self):
        return f"{self.full_name} : Табличная функция"


class DBStoredProcedure(DBScript):
    """
    Хранимая процедура базы данных.
    """
    __tablename__ = "DBStoredProcedure"
    id = Column(ForeignKey("DBScript.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity":"Хранимая процедура"
    }

    def __repr__(self):
        return f"{self.full_name} : Хранимая процедура"


class DBTrigger(DBScript):
    """
    Триггер, привязанный к таблице.
    """
    __tablename__ = "DBTrigger"
    id = Column(ForeignKey("DBScript.id"), primary_key=True)
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
            database_name=refs["database"].name,
            database_object_id=original.database_object_id,
            is_update=original.is_update,
            is_delete=original.is_delete,
            is_insert=original.is_insert,
            sql=original.sql,
            last_update=original.last_update,
            table=refs["table"],
            database=refs["database"]
        )

class DBTable(DatabaseObject):
    """
    Таблица из базы данных исследуемой системы.
    """
    __tablename__ = "DBTable"
    id = Column(Integer, ForeignKey("DatabaseObject.id"), primary_key=True)
    database = relationship(
        "Database", back_populates="tables",
        foreign_keys=[DatabaseObject.database_id])
    triggers = relationship(
        "DBTrigger",
        collection_class=attribute_mapped_collection("full_name"),
        back_populates="table", foreign_keys=[DBTrigger.table_id])

    __mapper_args__ = {
        "polymorphic_identity":"Таблица"
    }

    def __repr__(self):
        return f"{self.full_name} : Таблица"
    
    @classmethod
    def create_from(cls, original, **refs):
        if "parent" not in refs:
            raise ModelException("Пропущен именованный параметр parent")
        return DBTable(
            name=original.name,
            schema=original.schema,
            database_name=refs["parent"].name,
            database_object_id=original.database_object_id,
            last_update=original.last_update,
            database=refs["parent"]
        )
    
    def get_regexp(self):
        """
        Получение регулярки для таблицы.

        Итоговое выражение имеет такой вид:

        (?P<select>варианты для всех имён во всех контекстах)|(?P<update>...)|(?P...

        С таблицей проводятся операции select, insert, update, delete, truncate, drop.

        Имя таблицы может иметь следующий вид:
            * имя_таблицы
            * схема.имя_таблицы
            * база.схема.имя_таблицы
        
        Одно и то же действие (вставка, выборка) может быть оформлено синтаксически по-разному;

        Итоговое регулярное выражение формируется как комбинация всех этих вариантов.
        """
        various_names = [
            self.name,
            f"{self.schema}.{self.name}",
            self.full_name
        ]
        chunks = []
        for action in ["select", "update", "insert", "delete", "truncate", "drop"]:
            chunks.append(fr"(?P<{action}>")
            for name in various_names:
                if action == "select":
                    chunks.append(fr" *join {name} | *{name},|from {name}[ ,]")
                elif action == "update":
                    chunks.append(fr"update {name} ")
                elif action == "insert":
                    chunks.append(fr"into {name} |insert {name}")
                elif action == "delete":
                    chunks.append(fr"delete from {name} |delete {name} ")
                elif action == "truncate":
                    chunks.append(fr"truncate {name} ")
                elif action == "drop":
                    chunks.append(fr"drop table {name} ")
                if name != various_names[2]:
                    chunks.append(r"|")
            if action != "drop":
                chunks.append(r")|")
            else:
                chunks.append(r")")
        return "".join(chunks)


class Database(Node):
    """
    База данных в исследуемой системе
    """
    __tablename__ = "Database"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    tables = relationship(
        "DBTable",
        collection_class=attribute_mapped_collection("full_name"),
        back_populates="database",
        foreign_keys=[DBTable.database_id])
    views = relationship(
        "DBView",
        collection_class=attribute_mapped_collection("full_name"),
        back_populates="database",
        foreign_keys=[DBView.database_id])
    procedures = relationship(
        "DBStoredProcedure",
        collection_class=attribute_mapped_collection("full_name"),
        back_populates="database",
        foreign_keys=[DBStoredProcedure.database_id])
    table_functions = relationship(
        "DBTableFunction",
        collection_class=attribute_mapped_collection("full_name"),
        back_populates="database",
        foreign_keys=[DBTableFunction.database_id])
    scalar_functions = relationship(
        "DBScalarFunction",
        collection_class=attribute_mapped_collection("full_name"),
        back_populates="database",
        foreign_keys=[DBScalarFunction.database_id])
    triggers = relationship(
        "DBTrigger",
        collection_class=attribute_mapped_collection("full_name"),
        back_populates="database",
        foreign_keys=[DBTrigger.database_id])
    executables = relationship(
        "DBScript",
        collection_class=attribute_mapped_collection("full_name"),
        back_populates="database",
        foreign_keys=[DBScript.database_id])
    connections = relationship(
        "ClientConnection",
        collection_class=attribute_mapped_collection("name"),
        back_populates="database",
        foreign_keys=[ClientConnection.database_id])

    __mapper_args__ = {
        "polymorphic_identity":"База данных"
    }

    def __repr__(self):
        return self.name
 