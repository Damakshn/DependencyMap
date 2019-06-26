declare @refs TABLE (
	referencing_object_id INT
	,referenced_object_id INT
)

declare @tmp table (
	db_name VARCHAR(50)
	,[schema] VARCHAR(50)
	,name VARCHAR(500)
	,database_object_id BIGINT
)

insert into @tmp
SELECT
	DB_NAME() AS db_name
	,s.name AS [schema]
	,o.name AS name
	,m.object_id AS database_object_id
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id = m.object_id
JOIN sys.schemas s ON o.schema_id = s.schema_id
WHERE o.type in ('P', 'TR', 'TF', 'FN', 'V')

declare @referencing_object_id int, @long_name varchar(500)
declare script_cursor cursor for select database_object_id, [schema]+'.'+name from @tmp

open script_cursor
fetch next from script_cursor into @referencing_object_id, @long_name
while @@FETCH_STATUS = 0
begin
	begin try
		INSERT INTO @refs
		SELECT distinct @referencing_object_id, referenced_id FROM
        sys.dm_sql_referenced_entities(@long_name,'OBJECT')
        WHERE referenced_id is not NULL
	end try
	begin catch
	end catch
	fetch next from script_cursor into @referencing_object_id, @long_name
end
close script_cursor
deallocate script_cursor

select *  from @refs