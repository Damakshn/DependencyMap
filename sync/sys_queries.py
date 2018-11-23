from sqlalchemy.sql import text, select

all_tables = select([
    text(
        """
        t.object_id as database_object_id,
        s.name as schema_name,
        t.name as name,
        t.modify_date as last_update
        """)]).\
    select_from(text("sys.tables t join sys.schemas s on t.schema_id = s.schema_id")).alias()

all_triggers = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        o.parent_object_id as table_id,
        m.definition as definition
    from 
        sys.sql_modules m
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type = 'TR'
    """)

all_procedures = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as definition
    from 
        sys.sql_modules m
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type = 'P'
    """)

all_views = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as definition
    from 
        sys.sql_modules m 
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where
        o.type = 'V'
    """)

all_functions = text(
    """
    select 
        m.object_id,
        s.name as [schema]_name,
        o.name as object_name,
        o.type,
        o.modify_date,
        m.definition
    from 
        sys.sql_modules m 
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where o.type in ('TF', 'FN')
    """)