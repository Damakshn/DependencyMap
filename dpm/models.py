from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text, Boolean, SmallInteger
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
import datetime

BaseDPM = declarative_base()


class ModelException(Exception):
    pass


class Node(BaseDPM):
    """
    Компоненты исследуемой информационной системы, которые
    взаимодействуют друг с другом и соединяются связями.
    """
    __tablename__ = "Node"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    # когда последний раз обновлялись связи
    last_revision = Column(DateTime)
    # когда последний раз сверялись с оригиналом
    last_update = Column(DateTime)
    type = Column(String(50))
    id_broken = Column(Boolean, default=False, nullable=False)
    is_dummy = Column(Boolean, default=False, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "Объект"
    }

    def update_from(self, original):
        """
        Обновляет данные основных полей объекта данными из оригинала.
        """
        # проверяем наличие всех синхронизируемых полей в оригинале
        for field in self.sync_fields:
            if not hasattr(original, field):
                raise ModelException(f"Поле {field} не найдено в оригинале объекта {self.__class__}")
        for field in self.sync_fields:
            setattr(self, field, getattr(original, field))
        self.last_update = getattr(original, "last_update", datetime.datetime.now())

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


class Edge(BaseDPM):
    """
    Связи между объектами Node.
    """
    __tablename__ = "Edge"
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
    # если True, то один из соединяемых объектов является фиктивным
    is_dummy = Column(Boolean, default=False, nullable=False)
    # поля, описывающие что объект from_node делает с объектом to_node
    # числовое значение указывает на число совпадений (кол-во использований)
    contain = Column(Boolean, default=False, nullable=False)
    call = Column(SmallInteger, default=0, nullable=False)
    select = Column(SmallInteger, default=0, nullable=False)
    insert = Column(SmallInteger, default=0, nullable=False)
    update = Column(SmallInteger, default=0, nullable=False)
    delete = Column(SmallInteger, default=0, nullable=False)
    truncate = Column(Boolean, default=False, nullable=False)
    drop = Column(Boolean, default=False, nullable=False)
    trigger = Column(Boolean, default=False, nullable=False)
    

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

"""
добавляем классу Node зависимости от Edge
входящие и исходящие связи;
при удалении ноды все входящие/исходящие связи тоже должны быть удалены
"""
Node.edges_in = relationship(
    "Edge",
    foreign_keys=[Edge.to_node_id],
    cascade="all, delete",
    passive_deletes=True)
Node.edges_out = relationship(
    "Edge",
    foreign_keys=[Edge.from_node_id],
    cascade="all, delete",
    passive_deletes=True)


class DatabaseObject(Node):
    """
    Объект, хранящийся в базе данных информационной системы
    (таблица или скрипт (процедура, представление и т.д.)).

    SQL Server идентифицирует все такие объекты внутренним object_id,
    каждый объект привязан к определённой схеме внутри своей БД.

    При взаимодействии с объектом могут использоваться 3 различных варианта
    написания его имени - короткое (Имя), длинное (Схема.Имя) и полное
    (База.Схема.Имя).

    Каждый экземпляр этого класса умеет генерировать большое регулярное
    выражения для поиска упоминаний этого объекта (процедуры, функции,
    таблицы и т.д.) в текстах sql-запросов на клиенте или в БД.

    Если, например, процедура из БД1 обращается к таблице из БД2, то
    допускается использовать только полное имя таблицы, поэтому
    регулярки для "родной" и для "чужой" базы отличаются. Запросы,
    направляемые с клиента (например из компонента TADOQuery) тоже работают
    в контексте определённой БД (той, с которой соединяется подключённый
    к TADOQuery компонент TADOConnection), поэтому данное правило
    распространяется и на них тоже.
    """
    __tablename__ = "DatabaseObject"
    id = Column(ForeignKey("Node.id"), primary_key=True)
    database_id = Column(Integer, nullable=False)
    database_object_id = Column(Integer, nullable=False)
    schema = Column(String(30), nullable=False)
    database_name = Column(String(120), nullable=False)

    @property
    def long_name(self):
        return f"{self.schema}.{self.name}"

    @property
    def full_name(self):
        return f"{self.database_name}.{self.schema}.{self.name}"

    @property
    def sql_actions(self):
        """
        Список действий, которые можно осуществлять с объектом
        при его использовании в sql-коде.
        """
        return []

    def get_regexp_universal(self, actions, names):
        """
        Универсальный метод генерации регулярок для объектов БД.

        actions - список действий, которые будем искать
        (select, exec, delete etc.)
        names - список вариантов написания имени объекта
        (короткое, длинное, полное).

        Одно и то же действие (вставка, выборка) может быть
        оформлено синтаксически по-разному, итоговое регулярное
        выражение формируется как комбинация всех этих вариантов.

        Результат имеет примерно такой вид:

        (?P<select>варианты для всех имён во всех контекстах)|(?P<update>...)|(?P...

        или

        (?P<select> *join table1 | *table1,|from table1[ ,])|(?P<update>...)|(?P...
        """
        chunks = []
        for action in actions:
            chunks.append(fr"(?P<{action}>")
            for name in names:
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
                if name != names[len(names) - 1]:
                    chunks.append(r"|")
            if action != actions[len(actions) - 1]:
                chunks.append(r")|")
            else:
                chunks.append(r")")
        return "".join(chunks)

    def get_regexp_for_home_db(self):
        """
        Получение регулярки для поиска в скриптах "родной" БД.

        В этом случае используются все три варианта написания
        имени объекта: короткое, длинное и полное
        (Название, Схема.Название, БД.Схема.Название)
        """
        names = [
            self.name,
            f"{self.schema}.{self.name}",
            self.full_name
        ]
        return self.get_regexp_universal(self.sql_actions, names)

    def get_regexp_for_external_db(self):
        """
        Получение регулярки для поиска в скриптах "чужой" БД.

        В этом случае используются только полное имя объекта -
        БД.Схема.Название
        """
        return self.get_regexp_universal(self.sql_actions, [self.full_name])


class SQLQueryMixin():
    """
    Произвольный SQL-запрос.

    Помимо исходного кода самого запроса хранит также контрольную сумму,
    которая проверяется при синхронизации с оригиналом для избежания ненужных
    обновлений и, как следствие, пересчёта зависимостей.
    """
    crc32 = Column(Integer)

    @declared_attr
    def sql(cls):
        return deferred(Column(Text, nullable=False))


class ClientQuery(Node, SQLQueryMixin):
    """
    Компонент Delphi, содержащий SQL-запрос.

    Любой компонент привязан к какой-то форме в приложении и
    взаимодействует с базой данных посредством компонента TADOConnection,
    который за ним закреплён.

    Чтобы синхронизировать компонент, необходимо прочитать .dfm-файл,
    содержащий описание формы, на которой он расположен, из-за этого
    невозможно вычленить точную дату, когда оригинал компонента был
    изменён.
    """
    __tablename__ = "ClientQuery"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    component_type = Column(String(120), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "Клиентский запрос"
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

        Дата обновления ставится немножко костыльно, так как
        узнать реальную дату обновления компонента невозможно.
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


class Form(Node):
    """
    Delphi-форма с компонентами.

    Если DFM-файл с описанием формы не удалось распарсить, то
    поле is_broken ставится в True, а в поле parsing_error_message пишется
    ошибка, которую выдал парсер.
    """
    __tablename__ = "Form"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    path = Column(String(1000), nullable=False)
    alias = Column(String(50))
    parsing_error_message = Column(String(300))

    __mapper_args__ = {
        "polymorphic_identity": "Форма"
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
    # заполняется при создании из компонента
    database_name = Column(String(50))
    # если is_verified True, то данные соединения проверены вручную
    # и связи подключённых к нему компонентов можно анализировать
    is_verified = Column(Boolean, default=False, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "Компонент-соединение"
    }

    @property
    def sync_fields(self):
        return ["database_name"]

    @classmethod
    def create_from(cls, original, **refs):
        """
        Создаёт модель клиентского соединения из оригинального
        компонента в исходниках
        """
        if "parent" not in refs:
            raise ModelException("Пропущен именованный параметр parent")
        return ClientConnection(
            name=original.full_name,
            database_name=original.database,
            application=refs["parent"]
        )

    def __repr__(self):
        return f"Соединение {self.name} ({'???' if self.database is None else self.database.name})"


class Application(Node):
    """
    Клиентское приложение, написанное на Delphi.
    """
    __tablename__ = "Application"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)
    path = Column(String(1000), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "АРМ"
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
    Процедура/функция/представление/триггер из базы данных исследуемой системы.
    """
    __tablename__ = "DBScript"
    id = Column(Integer, ForeignKey("DatabaseObject.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "Запрос в БД"
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

    @property
    def sql_actions(self):
        """
        Список действий, которые можно осуществлять со скриптом
        при его использовании в sql-коде.
        """
        return ["select", "exec"]


class DBView(DBScript):
    """
    Представление базы данных.
    """
    __tablename__ = "DBView"
    id = Column(ForeignKey("DBScript.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity": "Представление"
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
        "polymorphic_identity": "Скалярная функция"
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
        "polymorphic_identity": "Табличная функция"
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
        "polymorphic_identity": "Хранимая процедура"
    }

    def __repr__(self):
        return f"{self.full_name} : Хранимая процедура"


class DBTrigger(DBScript):
    """
    Триггер, привязанный к таблице.
    """
    __tablename__ = "DBTrigger"
    id = Column(ForeignKey("DBScript.id"), primary_key=True)
    is_update = Column(Boolean, nullable=False)
    is_delete = Column(Boolean, nullable=False)
    is_insert = Column(Boolean, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "Триггер"
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

    __mapper_args__ = {
        "polymorphic_identity": "Таблица"
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

    @property
    def sql_actions(self):
        """
        Список действий, которые можно осуществлять с таблицей
        при обращении к ней в sql-коде.
        """
        return ["select", "update", "insert", "delete", "truncate", "drop"]


class Database(Node):
    """
    База данных в исследуемой системе
    """
    __tablename__ = "Database"
    id = Column(Integer, ForeignKey("Node.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "База данных"
    }

    def __repr__(self):
        return self.name
