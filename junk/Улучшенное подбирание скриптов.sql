declare @tmp table (
	name VARCHAR(500)
	,last_update DATETIME
	,database_object_id BIGINT
	,[schema] VARCHAR(50)
	,db_name VARCHAR(50)
	,sql NVARCHAR(max)
	,id_broken BIT
	)

DECLARE @sinchole BIGINT

INSERT INTO @tmp
SELECT o.name AS name
	,o.modify_date AS last_update
	,m.object_id AS database_object_id
	,s.name AS [schema]
	,DB_NAME() AS db_name
	,m.DEFINITION AS [sql]
	,0 AS is_broken
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id = m.object_id
JOIN sys.schemas s ON o.schema_id = s.schema_id
WHERE o.type = 'P'

DECLARE @object_id BIGINT
	,@long_name VARCHAR(500)

DECLARE script_cursor CURSOR
FOR
SELECT database_object_id
	,[schema] + '.' + name AS long_name
FROM @tmp

OPEN script_cursor

FETCH NEXT
FROM script_cursor
INTO @object_id
	,@long_name

WHILE @@FETCH_STATUS = 0
BEGIN
	BEGIN TRY
		SELECT @sinchole = (
				SELECT TOP (1) referenced_id
				FROM sys.dm_sql_referenced_entities(@long_name, 'OBJECT')
				WHERE referenced_id IS NOT NULL
				)
	END TRY

	BEGIN CATCH
		UPDATE @tmp
		SET id_broken = 1
		WHERE database_object_id = @object_id
	END CATCH

	FETCH NEXT
	FROM script_cursor
	INTO @object_id
		,@long_name
END

CLOSE script_cursor

DEALLOCATE script_cursor

SELECT *
FROM @tmp

