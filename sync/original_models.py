import datetime
import binascii
from .common_classes import Original
from dataclasses import dataclass, field
from sqlalchemy.sql import text
from common_functions import clear_sql

# ToDo метод query_all и методы, возвращающие несколько объектов, должны возвращать словарь
# словарь создаётся по длинному имени объектов, нужно изменить запросы, чтобы длинное имя там было


class DBOriginal(Original):
    name: str
    last_update: datetime.datetime

    @classmethod
    def key_field(cls):
        return "name"

@dataclass
class OriginalDatabaseObject(DBOriginal):
    """
    Оригинал объекта базы данных

    Помимо имени и даты обновления, хранит внутренний object_id объекта, 
    которым пользуется SQL Server и имя схемы
    """
    database_object_id: int
    schema: str
    db_name: str
    long_name: str = field(init=False)
    full_name: str = field(init=False)

    def __post_init__(self):
        self.long_name = f"{self.schema}.{self.name}"
        self.full_name = f"{self.db_name}.{self.schema}.{self.name}"

    @classmethod
    def query_all(cls):
        return None
    
    @classmethod
    def query_by_id(cls):
        return None

    @classmethod
    def get_all(cls, conn):
        """
        Возвращает коллекцию объектов-оригиналов, содержащую все объекты
        данного типа из той базы, с которой работает соединение conn.

        Тип коллекции - словарь, ключ - поле full_name, т.е. База.Схема.Название.
        """
        query = cls.query_all
        # dict comprehension
        return {
            obj.full_name: obj 
            for obj in [cls(**record) for record in conn.execute(query)]
        }
    
    @classmethod
    def get_by_id(cls, conn, id):
        """
        Возвращает оригинал объекта по его object_id в базе данных.
        """
        record = conn.execute(cls.query_by_id, id=id)
        if record:
            return cls(**record)
        return None


@dataclass
class OriginalScript(OriginalDatabaseObject):
    """
    Оригинал скриптового объекта (процедуры/функции и т.д.)
    """
    sql: str
    crc32: int = field(init=False)

    def __post_init__(self):
        """
        Вычищаем исходники при создании объекта и
        считаем контрольную сумму
        """
        super().__post_init__()
        self.sql = clear_sql(self.sql)
        self.crc32 = binascii.crc32(self.sql.encode("utf-8"))


@dataclass
class OriginalDatabase(DBOriginal):
    pass

    @classmethod
    def fetch_from_metadata(cls, conn):
        """
        Создаёт объект-оригинал на основе метаданных БД
        """
        query = text(
            """
            select
                DB_NAME() as name,
                max(modify_date) as last_update
            from
                sys.objects
            where 
                schema_id = 1
                and type in ('U','TR', 'P', 'V', 'TF', 'FN')""")
        meta = conn.execute(query).first()
        return cls(**meta)

@dataclass
class OriginalTable(OriginalDatabaseObject):
    """
    Оригинал таблицы базы данных
    """

    @classmethod
    def query_all(cls, conn):
        return text(
            """
            select
                t.name as name,
                t.modify_date as last_update,
                t.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name
            from
                sys.tables t
                join sys.schemas s on t.schema_id = s.schema_id""")
    
    @classmethod
    def query_by_id(cls):
        return text(
            """
            select
                t.name as name,
                t.modify_date as last_update,
                t.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name
            from
                sys.tables t
                join sys.schemas s on t.schema_id = s.schema_id
            where
                t.object_id = :id""")


@dataclass
class OriginalTrigger(OriginalScript):
    """
    Оригинал триггера

    Хранит внутренний object_id таблицы, к которой прикреплён триггер
    и флаги, указывающие на то, к какой sql-операции привязан триггер.
    """
    table_id: int
    is_update: bool
    is_delete: bool
    is_insert: bool

    @classmethod
    def query_all(cls):
        return text(
            """
            select
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql],
                o.parent_object_id as table_id,
                OBJECTPROPERTY(m.object_id, 'ExecIsUpdateTrigger') AS is_update,
                OBJECTPROPERTY(m.object_id, 'ExecIsDeleteTrigger') AS is_delete, 
                OBJECTPROPERTY(m.object_id, 'ExecIsInsertTrigger') AS is_insert
            from 
                sys.sql_modules m
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where 
                o.type = 'TR'""")
    
    @classmethod
    def query_by_id(cls):
        return text(
            """
            select 
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql],
                o.parent_object_id as table_id,
                OBJECTPROPERTY(m.object_id, 'ExecIsUpdateTrigger') AS is_update,
                OBJECTPROPERTY(m.object_id, 'ExecIsDeleteTrigger') AS is_delete, 
                OBJECTPROPERTY(m.object_id, 'ExecIsInsertTrigger') AS is_insert
            from 
                sys.sql_modules m
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where 
                o.type = 'TR'
                and m.object_id = :id""")
    
    @classmethod
    def get_triggers_for_table(cls, conn, table_id):
        """
        Возвращает коллекцию триггеров для одной таблицы по её object_id
        в БД.

        Тип коллекции - словарь, ключ - поле full_name.
        """
        query = text(
            """
            select 
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql],
                o.parent_object_id as table_id,
                OBJECTPROPERTY(m.object_id, 'ExecIsUpdateTrigger') AS is_update,
                OBJECTPROPERTY(m.object_id, 'ExecIsDeleteTrigger') AS is_delete, 
                OBJECTPROPERTY(m.object_id, 'ExecIsInsertTrigger') AS is_insert
            from
                sys.sql_modules m
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where 
                o.type = 'TR'
                and o.parent_object_id = :table_id""")
        # dict comprehension
        return {
            obj.full_name: obj
            for obj in [
                cls(**record) 
                for record in conn.execute(query, table_id=table_id)
            ]
        }


@dataclass
class OriginalProcedure(OriginalScript):
    """
    Оригинал хранимой процедуры
    """

    @classmethod
    def query_all(cls):
        return text(
            """
            select
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql]
            from 
                sys.sql_modules m
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where 
                o.type = 'P'""")
    
    @classmethod
    def query_by_id(cls):
        return text(
            """
            select 
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql]
            from 
                sys.sql_modules m
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where 
                o.type = 'P'
                and m.object_id = :id""")


@dataclass
class OriginalView(OriginalScript):
    """
    Оригинал представления
    """

    @classmethod
    def query_all(cls):
        return text(
            """
            select
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql]
            from 
                sys.sql_modules m 
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where
                o.type = 'V'""")
    
    @classmethod
    def query_by_id(cls):
        return text(
            """
            select
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql]
            from 
                sys.sql_modules m 
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where
                o.type = 'V'
                and m.object_id = :id""")


@dataclass
class OriginalTableFunction(OriginalScript):
    """
    Оригинал табличной функции
    """

    @classmethod
    def query_all(cls):
        return text(
            """
            select 
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql]
            from 
                sys.sql_modules m 
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where
                o.type = 'TF'""")
    
    @classmethod
    def query_by_id(cls):
        return text(
            """
            select 
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql]
            from 
                sys.sql_modules m 
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where 
                o.type = 'TF'
                and m.object_id = :id""")


@dataclass
class OriginalScalarFunction(OriginalScript):
    """
    Оригинал скалярной функции
    """ 

    @classmethod
    def query_all(cls):
        return text(
            """
            select 
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql]
            from 
                sys.sql_modules m 
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where 
                o.type ='FN'""")
    
    @classmethod
    def query_by_id(cls):
        return text(
            """
            select 
                o.name as name,
                o.modify_date as last_update,
                m.object_id as database_object_id,
                s.name as [schema],
                DB_NAME() as db_name,
                m.definition as [sql]
            from 
                sys.sql_modules m 
                join sys.objects o on o.object_id = m.object_id
                join sys.schemas s on o.schema_id = s.schema_id
            where 
                o.type ='FN'
                and m.object_id = :id""")

@dataclass
class OriginalSystemReferense(Original):
    """
    Запись о системной зависимости из внутренних таблиц SQL Server
    """
    referenced_id: int

    @classmethod
    def get_referenses_for_object(cls, conn, obj_long_name):
        """
        Возвращает коллекцию object_id объектов, от которых зависит объект, чьё
        значение long_name (Схема.Название) передано в качестве аргумента.

        Тип коллекции - словарь, ключ - object_id
        """
        query = text(
            """
            SELECT referenced_id FROM
            sys.dm_sql_referenced_entities(:obj_long_name,'OBJECT')""")
        # dict comprehension
        return {
            obj.referenced_id: obj
            for obj in [
                cls(**record) 
                for record in conn.execute(query, obj_long_name=obj_long_name)
            ]
        }
