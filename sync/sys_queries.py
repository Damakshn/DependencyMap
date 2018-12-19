from sqlalchemy.sql import text

all_tables = text(
    """
    select
        t.object_id as database_object_id,
        s.name as [schema],
        t.name as name,
        t.modify_date as last_update
    from
	    sys.tables t
	    join sys.schemas s on t.schema_id = s.schema_id
    """)

get_specific_table = text(
    """
    select
        t.object_id as database_object_id,
        s.name as [schema],
        t.name as name,
        t.modify_date as last_update
    from
	    sys.tables t
	    join sys.schemas s on t.schema_id = s.schema_id
    where
        t.object_id = :id
    """)

all_triggers = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        o.parent_object_id as table_id,
		OBJECTPROPERTY(m.object_id, 'ExecIsUpdateTrigger') AS is_update,
		OBJECTPROPERTY(m.object_id, 'ExecIsDeleteTrigger') AS is_delete, 
		OBJECTPROPERTY(m.object_id, 'ExecIsInsertTrigger') AS is_insert,
        m.definition as [sql]
    from 
        sys.sql_modules m
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type = 'TR'
    """)

triggers_for_table = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        o.parent_object_id as table_id,
		OBJECTPROPERTY(m.object_id, 'ExecIsUpdateTrigger') AS is_update,
		OBJECTPROPERTY(m.object_id, 'ExecIsDeleteTrigger') AS is_delete, 
		OBJECTPROPERTY(m.object_id, 'ExecIsInsertTrigger') AS is_insert,
        m.definition as [sql]
    from 
        sys.sql_modules m
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type = 'TR'
        and o.parent_object_id = :table_id
    """
)

get_specific_trigger = text(
     """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        o.parent_object_id as table_id,
		OBJECTPROPERTY(m.object_id, 'ExecIsUpdateTrigger') AS is_update,
		OBJECTPROPERTY(m.object_id, 'ExecIsDeleteTrigger') AS is_delete, 
		OBJECTPROPERTY(m.object_id, 'ExecIsInsertTrigger') AS is_insert,
        m.definition as [sql]
    from 
        sys.sql_modules m
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type = 'TR'
        and m.object_id = :id
    """
)

all_procedures = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as [sql]
    from 
        sys.sql_modules m
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type = 'P'
    """)

get_specific_procedure = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as [sql]
    from 
        sys.sql_modules m
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type = 'P'
        and m.object_id = :id
    """
)

all_views = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as [sql]
    from 
        sys.sql_modules m 
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where
        o.type = 'V'
    """)

get_specific_view = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as [sql]
    from 
        sys.sql_modules m 
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where
        o.type = 'V'
        and m.object_id = :id
    """)

all_scalar_functions = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as [sql]
    from 
        sys.sql_modules m 
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type ='FN'
    """)

get_specific_scalar_function = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as [sql]
    from 
        sys.sql_modules m 
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type ='FN'
        and m.object_id = :id
    """)

all_table_functions = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as [sql]
    from 
        sys.sql_modules m 
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where
        o.type = 'TF'
    """)

get_specific_table_function = text(
    """
    select 
        m.object_id as database_object_id,
        s.name as [schema],
        o.name as name,
        o.modify_date as last_update,
        m.definition as [sql]
    from 
        sys.sql_modules m 
        join sys.objects o on o.object_id = m.object_id
        join sys.schemas s on o.schema_id = s.schema_id
    where 
        o.type = 'TF'
        and m.object_id = :id
    """)

database_metadata = text(
    """
    select
        DB_NAME() as name,
        max(modify_date) as last_update
    from
	    sys.objects
	where 
		schema_id = 1
		and type in ('U','TR', 'P', 'V', 'TF', 'FN')
    """)
